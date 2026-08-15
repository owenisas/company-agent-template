#!/usr/bin/env bash
# Foreground launcher for the company-agent webui.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [[ -z "${SECRET_KEY:-}" && -f "$ROOT/runtime/secret" ]]; then
  # shellcheck disable=SC1091
  SECRET_KEY="$(tr -d '[:space:]' < "$ROOT/runtime/secret")"
  export SECRET_KEY
fi

if [[ -z "${SECRET_KEY:-}" ]]; then
  echo "SECRET_KEY is not set. Put it in the environment or runtime/secret." >&2
  exit 1
fi

export WEBUI_PORT="${WEBUI_PORT:-8080}"
export WEBUI_BIND="${WEBUI_BIND:-0.0.0.0}"
export HERMES_BIN="${HERMES_BIN:-hermes}"
export HERMES_PROVIDER="${HERMES_PROVIDER:-xai-oauth}"
export HERMES_MODEL="${HERMES_MODEL:-grok-4.6}"
export HERMES_REASONING_EFFORT="${HERMES_REASONING_EFFORT:-extra-high}"

PYTHON="${ROOT}/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  python3 -m venv "$ROOT/.venv"
  PYTHON="${ROOT}/.venv/bin/python"
  "$PYTHON" -m pip install -q --upgrade pip
  "$PYTHON" -m pip install -q -r "$ROOT/requirements.txt"
fi

exec "$PYTHON" -m uvicorn backend.app:app \
  --host "$WEBUI_BIND" \
  --port "$WEBUI_PORT"
