"""Runtime configuration from the environment."""

from __future__ import annotations

import os
from pathlib import Path

WEBUI_ROOT = Path(__file__).resolve().parent.parent
RUNTIME_DIR = WEBUI_ROOT / "runtime"
FRONTEND_DIR = WEBUI_ROOT / "frontend"
USERS_PATH = RUNTIME_DIR / "users.json"
JOBS_DIR = RUNTIME_DIR / "jobs"

COOKIE_NAME = "webui_session"
COOKIE_MAX_AGE = 60 * 60 * 12
PBKDF2_ITERATIONS = 210_000


def secret_key() -> str:
    key = os.environ.get("SECRET_KEY", "").strip()
    if not key:
        raise RuntimeError("SECRET_KEY is not set")
    return key


def webui_port() -> int:
    raw = os.environ.get("WEBUI_PORT", "8080").strip() or "8080"
    return int(raw)


def bind_host() -> str:
    return os.environ.get("WEBUI_BIND", "0.0.0.0").strip() or "0.0.0.0"


def admins_from_env() -> frozenset[str]:
    raw = os.environ.get("WEBUI_ADMINS", "")
    return frozenset(part.strip() for part in raw.split(",") if part.strip())


def hermes_bin() -> str:
    return os.environ.get("HERMES_BIN", "hermes").strip() or "hermes"


def hermes_provider() -> str:
    return os.environ.get("HERMES_PROVIDER", "xai-oauth").strip() or "xai-oauth"


def hermes_model() -> str:
    return os.environ.get("HERMES_MODEL", "grok-4.6").strip() or "grok-4.6"


def hermes_reasoning() -> str:
    return os.environ.get("HERMES_REASONING_EFFORT", "extra-high").strip() or "extra-high"


def hermes_home() -> Path:
    raw = os.environ.get("HERMES_HOME", "").strip()
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".hermes"


def secure_cookie() -> bool:
    return os.environ.get("WEBUI_SECURE_COOKIE", "").strip().lower() in {"1", "true", "yes"}
