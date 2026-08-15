#!/usr/bin/env bash
# Idempotent fresh-VPS bootstrap for Ubuntu 24.04.
# Usage: sudo bash scripts/bootstrap.sh [git-clone-url]
set -euo pipefail

REPO_URL="${1:-}"
INSTALL_ROOT="${INSTALL_ROOT:-/opt/company-agent}"
SERVICE_USER="${SERVICE_USER:-company-agent}"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "run as root (sudo bash scripts/bootstrap.sh <git-url>)" >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y --no-install-recommends \
  ca-certificates curl git gnupg lsb-release \
  python3 python3-venv python3-pip python3.12 python3.12-venv

if ! command -v docker >/dev/null 2>&1; then
  apt-get install -y --no-install-recommends docker.io docker-compose-v2
  systemctl enable --now docker
fi

if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # installer puts uv in /root/.local/bin on a root run
  if [[ -x /root/.local/bin/uv ]]; then
    ln -sfn /root/.local/bin/uv /usr/local/bin/uv
  fi
fi

id -u "${SERVICE_USER}" >/dev/null 2>&1 || useradd --system --create-home --shell /usr/sbin/nologin "${SERVICE_USER}"

mkdir -p "${INSTALL_ROOT}"
if [[ -n "${REPO_URL}" && ! -d "${INSTALL_ROOT}/.git" ]]; then
  git clone "${REPO_URL}" "${INSTALL_ROOT}"
elif [[ ! -d "${INSTALL_ROOT}/.git" && ! -f "${INSTALL_ROOT}/README.md" ]]; then
  echo "no repo at ${INSTALL_ROOT}; pass a git URL" >&2
  exit 1
fi

cd "${INSTALL_ROOT}"
if [[ ! -f .env && -f .env.EXAMPLE ]]; then
  cp .env.EXAMPLE .env
  chmod 600 .env
fi
if [[ ! -f infra/.env && -f infra/.env.EXAMPLE ]]; then
  cp infra/.env.EXAMPLE infra/.env
  chmod 600 infra/.env
fi

if command -v docker >/dev/null 2>&1; then
  (cd infra && docker compose --env-file .env up -d || \
    echo "compose up skipped or failed — fill infra/.env and retry")
fi

chown -R "${SERVICE_USER}:${SERVICE_USER}" "${INSTALL_ROOT}" || true

cat <<EOF

Bootstrap finished.

Next:
  1. Edit ${INSTALL_ROOT}/.env and ${INSTALL_ROOT}/infra/.env (placeholders only).
  2. Copy governance/DECISIONS-NEEDED-template.md -> DECISIONS-NEEDED.md and fill TODOs.
  3. Install Hermes, then create profiles (see INSTALL.md):
       hermes profile create automation --no-alias
       hermes profile install ${INSTALL_ROOT}/distribution --name automation -y
       hermes profile create employee-a --no-alias --no-skills
  4. Run offline tests:
       cd ${INSTALL_ROOT}/services && python3 -m pytest tests/ -q
  5. Do not connect production CRM/Notion/finance until D020-D025 close.

EOF
