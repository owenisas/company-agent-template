"""Configuration layering (spec 13.4).

Precedence (later wins):

    compiled safe defaults
        < versioned non-secret environment config (file)
            < deployment secret *references* (process env)
                < short-lived request identity and purpose

An agent prompt or note MUST NOT modify server authorization configuration.
Request-layer overrides are limited to identity/purpose fields.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

from pydantic import BaseModel, Field

SAFE_DEFAULTS: dict[str, Any] = {
    "app_env": "testing",
    "log_level": "INFO",
    "database_url": "",
    "object_store_backend": "filesystem",
    "object_store_root": "/data/objects",
    "embedding_provider": "",
    "embedding_model": "",
    "embedding_dimensions": "",
    "otel_exporter_otlp_endpoint": "",
    "auth_issuer": "",
    "auth_audience": "company-agent",
    "notion_client_id": "",
    "notion_client_secret": "",
    "notion_redirect_uri": "",
    "principal_id": "",
    "purpose": "",
    "request_id": "",
    "trace_id": "",
}

FILE_KEYS = {
    "APP_ENV": "app_env",
    "LOG_LEVEL": "log_level",
    "DATABASE_URL": "database_url",
    "OBJECT_STORE_BACKEND": "object_store_backend",
    "OBJECT_STORE_ROOT": "object_store_root",
    "EMBEDDING_PROVIDER": "embedding_provider",
    "EMBEDDING_MODEL": "embedding_model",
    "EMBEDDING_DIMENSIONS": "embedding_dimensions",
    "OTEL_EXPORTER_OTLP_ENDPOINT": "otel_exporter_otlp_endpoint",
    "AUTH_ISSUER": "auth_issuer",
    "AUTH_AUDIENCE": "auth_audience",
    "NOTION_CLIENT_ID": "notion_client_id",
    "NOTION_CLIENT_SECRET": "notion_client_secret",
    "NOTION_REDIRECT_URI": "notion_redirect_uri",
}

REQUEST_OVERRIDE_KEYS = frozenset({"principal_id", "purpose", "request_id", "trace_id"})

# Fields a request/prompt MUST NOT change.
PROTECTED_KEYS = frozenset(SAFE_DEFAULTS) - REQUEST_OVERRIDE_KEYS


class Settings(BaseModel):
    app_env: str = "testing"
    log_level: str = "INFO"
    database_url: str = ""
    object_store_backend: str = "filesystem"
    object_store_root: str = "/data/objects"
    embedding_provider: str = ""
    embedding_model: str = ""
    embedding_dimensions: str = ""
    otel_exporter_otlp_endpoint: str = ""
    auth_issuer: str = ""
    auth_audience: str = "company-agent"
    notion_client_id: str = ""
    notion_client_secret: str = ""
    notion_redirect_uri: str = ""
    principal_id: str = ""
    purpose: str = ""
    request_id: str = ""
    trace_id: str = ""
    layers_applied: list[str] = Field(default_factory=list)

    @property
    def database_configured(self) -> bool:
        return bool(self.database_url) and "<PASSWORD>" not in self.database_url

    @property
    def embeddings_configured(self) -> bool:
        return bool(self.embedding_provider and self.embedding_model and self.embedding_dimensions)

    @property
    def notion_oauth_configured(self) -> bool:
        return bool(self.notion_client_id and self.notion_client_secret and self.notion_redirect_uri)


def parse_env_file(path: str | Path) -> dict[str, str]:
    parsed: dict[str, str] = {}
    text = Path(path).read_text(encoding="utf-8")
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :]
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip().strip("'").strip('"')
        parsed[key.strip()] = value
    return parsed


def _apply_file_map(target: dict[str, Any], raw: Mapping[str, str]) -> None:
    for env_key, field in FILE_KEYS.items():
        if env_key in raw:
            target[field] = raw[env_key]


def load_config(
    *,
    file_path: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    request: Mapping[str, Any] | None = None,
) -> Settings:
    """Resolve defaults < file < env < request (identity/purpose only)."""
    data = dict(SAFE_DEFAULTS)
    layers = ["defaults"]

    if file_path is not None:
        _apply_file_map(data, parse_env_file(file_path))
        layers.append("file")

    env_map = env if env is not None else os.environ
    applied_env = False
    for env_key, field in FILE_KEYS.items():
        if env_key in env_map and env_map[env_key] != "":
            data[field] = env_map[env_key]
            applied_env = True
    if applied_env:
        layers.append("env")

    if request:
        for key, value in request.items():
            if key in REQUEST_OVERRIDE_KEYS and value is not None:
                data[key] = value
            # Silently ignore attempts to override protected keys.
        layers.append("request")

    data["layers_applied"] = layers
    return Settings(**data)
