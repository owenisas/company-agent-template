"""Config layering precedence: defaults < file < env < request (spec 13.4)."""

from pathlib import Path

from packages.config import SAFE_DEFAULTS, load_config


def test_defaults_when_nothing_else_provided():
    cfg = load_config(env={})
    assert cfg.app_env == SAFE_DEFAULTS["app_env"]
    assert cfg.log_level == "INFO"
    assert cfg.auth_audience == "company-agent"
    assert cfg.layers_applied == ["defaults"]
    assert cfg.database_configured is False


def test_file_overrides_defaults(tmp_path: Path):
    env_file = tmp_path / "platform.env"
    env_file.write_text("APP_ENV=working\nLOG_LEVEL=DEBUG\n", encoding="utf-8")
    cfg = load_config(file_path=env_file, env={})
    assert cfg.app_env == "working"
    assert cfg.log_level == "DEBUG"
    assert cfg.layers_applied == ["defaults", "file"]


def test_env_overrides_file(tmp_path: Path):
    env_file = tmp_path / "platform.env"
    env_file.write_text("APP_ENV=working\nLOG_LEVEL=DEBUG\n", encoding="utf-8")
    cfg = load_config(
        file_path=env_file,
        env={"APP_ENV": "testing", "LOG_LEVEL": "WARNING"},
    )
    assert cfg.app_env == "testing"
    assert cfg.log_level == "WARNING"
    assert cfg.layers_applied == ["defaults", "file", "env"]


def test_request_overrides_only_identity_and_purpose(tmp_path: Path):
    env_file = tmp_path / "platform.env"
    env_file.write_text("APP_ENV=working\nAUTH_AUDIENCE=from-file\n", encoding="utf-8")
    cfg = load_config(
        file_path=env_file,
        env={"APP_ENV": "testing"},
        request={
            "principal_id": "employee-a",
            "purpose": "research",
            "request_id": "req_1",
            "trace_id": "trc_1",
            "app_env": "stable",
            "auth_audience": "evil",
            "database_url": "postgresql://kb_app:should-not-apply@x/y",
        },
    )
    assert cfg.principal_id == "employee-a"
    assert cfg.purpose == "research"
    assert cfg.request_id == "req_1"
    assert cfg.trace_id == "trc_1"
    assert cfg.app_env == "testing"
    assert cfg.auth_audience == "from-file"
    assert cfg.database_url == ""
    assert cfg.layers_applied == ["defaults", "file", "env", "request"]
