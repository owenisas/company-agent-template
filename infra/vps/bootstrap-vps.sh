#!/usr/bin/env bash
# Idempotent Ubuntu 24.04 bootstrap for a company Hermes VPS.
#
# Usage (as root, after replacing placeholders):
#   VPS_USER=<VPS_USER> DOMAIN=<DOMAIN> sudo -E bash infra/vps/bootstrap-vps.sh
#
# Optional:
#   PI_HOST=<pi-ip>          # if set, run scripts/migrate-from-pi.sh --apply
#   INSTALL_ROOT=/opt/company-agent
#   SKIP_COMPOSE=1           # install Docker but do not compose up
#   SKIP_HERMES_INSTALL=1
#
# PostgreSQL + pgvector is Docker-based (infra/vps/compose.yaml,
# image pgvector/pgvector:0.8.6-pg18-bookworm). Host apt postgresql is
# an alternative and is NOT installed here.
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "run as root: VPS_USER=<VPS_USER> DOMAIN=<DOMAIN> sudo -E bash $0" >&2
  exit 1
fi

VPS_USER="${VPS_USER:-<VPS_USER>}"
DOMAIN="${DOMAIN:-<DOMAIN>}"
INSTALL_ROOT="${INSTALL_ROOT:-/opt/company-agent}"
TEMPLATE_ROOT="${TEMPLATE_ROOT:-/home/${VPS_USER}/workspace/company-agent-template}"
HERMES_HOME="${HERMES_HOME:-/home/${VPS_USER}/.hermes}"
WORKSPACE="${WORKSPACE:-/home/${VPS_USER}/workspace}"

PLATFORM_REPO="${PLATFORM_REPO:-git@github.com:<GITHUB_ORG>/<COMPANY_PLATFORM_REPO>.git}"
TEMPLATE_REPO="${TEMPLATE_REPO:-git@github.com:<GITHUB_ORG>/company-agent-template.git}"
RUNTIME_REPO="${RUNTIME_REPO:-git@github.com:<GITHUB_ORG>/hermes-agent-platform.git}"

if [[ -z "${VPS_USER}" || "${VPS_USER}" == "<VPS_USER>" ]]; then
  echo "Set VPS_USER to the real login (replace the <VPS_USER> placeholder)." >&2
  exit 1
fi
if ! id -u "${VPS_USER}" >/dev/null 2>&1; then
  echo "user ${VPS_USER} does not exist — create it before bootstrap." >&2
  exit 1
fi
if [[ "${DOMAIN}" == "<DOMAIN>" ]]; then
  echo "WARNING: DOMAIN is still the <DOMAIN> placeholder. Continuing; fix DNS later."
fi
if [[ "${PLATFORM_REPO}" == *"<GITHUB_ORG>"* || "${RUNTIME_REPO}" == *"<GITHUB_ORG>"* ]]; then
  echo "WARNING: git URLs still contain <GITHUB_ORG> placeholders. Override PLATFORM_REPO / RUNTIME_REPO / TEMPLATE_REPO."
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y --no-install-recommends \
  ca-certificates curl git gnupg lsb-release rsync \
  python3 python3-venv python3-pip python3.12 python3.12-venv \
  python3-yaml

# Docker Engine + Compose plugin. pgvector runs in Compose, not via apt.
if ! command -v docker >/dev/null 2>&1; then
  apt-get install -y --no-install-recommends docker.io docker-compose-v2
  systemctl enable --now docker
fi
usermod -aG docker "${VPS_USER}" || true

if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  if [[ -x /root/.local/bin/uv ]]; then
    ln -sfn /root/.local/bin/uv /usr/local/bin/uv
  fi
  VPS_HOME="$(getent passwd "${VPS_USER}" | cut -d: -f6)"
  if [[ -x "${VPS_HOME}/.local/bin/uv" ]]; then
    ln -sfn "${VPS_HOME}/.local/bin/uv" /usr/local/bin/uv
  fi
fi

install -d -o "${VPS_USER}" -g "${VPS_USER}" \
  "${INSTALL_ROOT}" "${WORKSPACE}" "${HERMES_HOME}" \
  "/home/${VPS_USER}/.config/systemd/user" \
  "/home/${VPS_USER}/.local/bin"

clone_or_update() {
  local url="$1" dest="$2"
  if [[ "${url}" == *"<"* ]]; then
    echo "skip clone — URL still has a placeholder: ${url}"
    return 0
  fi
  if [[ -d "${dest}/.git" ]]; then
    echo "git pull ${dest}"
    sudo -u "${VPS_USER}" git -C "${dest}" pull --ff-only || \
      echo "WARNING: pull failed for ${dest} — check deploy keys."
  elif [[ -e "${dest}" && ! -d "${dest}/.git" ]]; then
    echo "WARNING: ${dest} exists and is not a git repo — skipped clone of ${url}"
  else
    echo "git clone ${url} ${dest}"
    sudo -u "${VPS_USER}" git clone "${url}" "${dest}"
  fi
}

# Three repos: company platform, public template, runtime fork.
clone_or_update "${PLATFORM_REPO}" "${INSTALL_ROOT}"
clone_or_update "${TEMPLATE_REPO}" "${TEMPLATE_ROOT}"
clone_or_update "${RUNTIME_REPO}" "${HERMES_HOME}/hermes-agent"

as_user() {
  sudo -u "${VPS_USER}" --preserve-env=HOME,PATH,HERMES_HOME \
    env HOME="/home/${VPS_USER}" "$@"
}

# Runtime venv (clone hermes-agent-platform → editable install).
if [[ "${SKIP_HERMES_INSTALL:-0}" != "1" && -d "${HERMES_HOME}/hermes-agent" ]]; then
  if [[ ! -x "${HERMES_HOME}/hermes-agent/.venv/bin/python" ]]; then
    as_user uv venv --python 3.12 "${HERMES_HOME}/hermes-agent/.venv" || \
      as_user python3.12 -m venv "${HERMES_HOME}/hermes-agent/.venv"
  fi
  if [[ -x "${HERMES_HOME}/hermes-agent/.venv/bin/python" ]]; then
    as_user "${HERMES_HOME}/hermes-agent/.venv/bin/python" -m pip install -U pip
    as_user env VIRTUAL_ENV="${HERMES_HOME}/hermes-agent/.venv" \
      uv pip install -e "${HERMES_HOME}/hermes-agent" || \
      as_user "${HERMES_HOME}/hermes-agent/.venv/bin/python" -m pip install -e "${HERMES_HOME}/hermes-agent"
    ln -sfn "${HERMES_HOME}/hermes-agent/.venv/bin/hermes" \
      "/home/${VPS_USER}/.local/bin/hermes"
    chown -h "${VPS_USER}:${VPS_USER}" "/home/${VPS_USER}/.local/bin/hermes" || true
  fi
fi

# Env templates (do not overwrite a filled .env).
if [[ -f "${INSTALL_ROOT}/infra/vps/.env.EXAMPLE" && ! -f "${INSTALL_ROOT}/infra/vps/.env" ]]; then
  cp "${INSTALL_ROOT}/infra/vps/.env.EXAMPLE" "${INSTALL_ROOT}/infra/vps/.env"
  chmod 600 "${INSTALL_ROOT}/infra/vps/.env"
  chown "${VPS_USER}:${VPS_USER}" "${INSTALL_ROOT}/infra/vps/.env"
fi
if [[ -f "${INSTALL_ROOT}/.env.EXAMPLE" && ! -f "${INSTALL_ROOT}/.env" ]]; then
  cp "${INSTALL_ROOT}/.env.EXAMPLE" "${INSTALL_ROOT}/.env"
  chmod 600 "${INSTALL_ROOT}/.env"
  chown "${VPS_USER}:${VPS_USER}" "${INSTALL_ROOT}/.env"
fi

# systemd user units (serve :9120, desktop-web :9121).
UNIT_DIR="/home/${VPS_USER}/.config/systemd/user"
cat > "${UNIT_DIR}/hermes-serve.service" <<UNIT
[Unit]
Description=Hermes headless backend (desktop app / API gateway)
After=network-online.target

[Service]
Type=simple
ExecStart=/home/${VPS_USER}/.local/bin/hermes serve --host 127.0.0.1 --port 9120 --skip-build
WorkingDirectory=/home/${VPS_USER}
Restart=on-failure
RestartSec=3
Environment=PATH=/home/${VPS_USER}/.local/bin:/home/${VPS_USER}/.hermes/node/bin:/usr/local/bin:/usr/bin:/bin
EnvironmentFile=-/home/${VPS_USER}/.hermes/notion-pat.env
Environment=HOME=/home/${VPS_USER}

[Install]
WantedBy=default.target
UNIT

cat > "${UNIT_DIR}/hermes-desktop-web.service" <<UNIT
[Unit]
Description=Hermes desktop renderer (browser build on :9121)
After=network-online.target hermes-serve.service

[Service]
Type=simple
WorkingDirectory=/home/${VPS_USER}/.hermes/hermes-agent/apps/desktop
ExecStart=/usr/bin/python3 /home/${VPS_USER}/.hermes/hermes-agent/apps/desktop/scripts/serve-web.py --bind 127.0.0.1 --port 9121 --root /home/${VPS_USER}/.hermes/hermes-agent/apps/desktop/dist-web --backend http://127.0.0.1:9120
Restart=on-failure
RestartSec=3
Environment=HOME=/home/${VPS_USER}
Environment=PATH=/home/${VPS_USER}/.local/bin:/home/${VPS_USER}/.hermes/node/bin:/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=default.target
UNIT
chown -R "${VPS_USER}:${VPS_USER}" "/home/${VPS_USER}/.config/systemd"

loginctl enable-linger "${VPS_USER}"
as_user systemctl --user daemon-reload || true
as_user systemctl --user enable hermes-serve.service hermes-desktop-web.service || true

if [[ -n "${PI_HOST:-}" ]]; then
  echo "PI_HOST=${PI_HOST} — running migrate-from-pi.sh --apply"
  as_user bash "${INSTALL_ROOT}/scripts/migrate-from-pi.sh" --apply "${PI_HOST}" "${PI_REMOTE_USER:-<remote-user>}" || \
    echo "WARNING: migrate --apply failed. Re-run after SSH to the old host works."
else
  echo "PI_HOST unset — skip restore. Later:"
  echo "  sudo -u ${VPS_USER} bash ${INSTALL_ROOT}/scripts/migrate-from-pi.sh --dry-run <pi-host>"
fi

if [[ "${SKIP_COMPOSE:-0}" != "1" && -f "${INSTALL_ROOT}/infra/vps/compose.yaml" ]]; then
  if grep -q '<postgres-password>\|<NOTION_API_TOKEN>\|<AUTH_SECRET>\|<EMBEDDING_API_KEY>' \
      "${INSTALL_ROOT}/infra/vps/.env" 2>/dev/null; then
    echo "infra/vps/.env still has placeholders — not starting Compose."
  else
    (cd "${INSTALL_ROOT}/infra/vps" && docker compose --env-file .env up -d) || \
      echo "compose up failed — fill infra/vps/.env and retry."
  fi
fi

cat <<EOF

Bootstrap finished for user=${VPS_USER} domain=${DOMAIN}

Next (see ${INSTALL_ROOT}/docs/MIGRATION-VPS.md):
  1. Rotate / replace every secret. Do not keep old-host production creds live.
  2. OUT OF BAND copy:
       ~/.hermes/dashboard-users.json          (0600)
       ~/.hermes/notion-pat.env                (0600)
       dashboard.company_auth.secret
       per-profile .env and auth.json
  3. Re-auth the model provider (device flow / API key) on the VPS.
  4. Configure Notion (PAT in notion-pat.env and/or NOTION_API_TOKEN in
     infra/vps/.env). Share the integration with the workspace.
  5. Fill ${INSTALL_ROOT}/infra/vps/.env (postgres, embeddings, Notion, auth).
  6. Start Hermes:
       sudo -u ${VPS_USER} systemctl --user start hermes-serve hermes-desktop-web
  7. Start the knowledge stack:
       cd ${INSTALL_ROOT}/infra/vps && docker compose --env-file .env up -d
  8. Point ${DOMAIN} (and TLS) at 127.0.0.1:9121 (UI) / :9120 (API)
     via Caddy/nginx. Ports are localhost-only by default.
  9. First-run checks, then decommission the old host.

EOF
