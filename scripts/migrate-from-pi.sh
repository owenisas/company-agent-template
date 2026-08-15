#!/usr/bin/env bash
# Move a one-host Pi (or other appliance) deployment onto a VPS.
# Generic helper. Review every path before running. Does not invent a
# profile mapping (D050).
#
# Usage (on the VPS, as an admin):
#   bash scripts/migrate-from-pi.sh [--dry-run|--apply] <pi-host> [remote-user]
#
# Default is --dry-run. Credentials, dashboard-users.json, notion-pat.env,
# PEMs, bot tokens, the dashboard auth secret, and per-profile .env/auth.json
# are transferred OUT OF BAND — never via git, never by this script
# inventing a secret channel.
set -euo pipefail

MODE="dry-run"
if [[ "${1:-}" == "--apply" ]]; then
  MODE="apply"
  shift
elif [[ "${1:-}" == "--dry-run" ]]; then
  MODE="dry-run"
  shift
fi

PI_HOST="${1:-}"
REMOTE_USER="${2:-<remote-user>}"
DEST_ROOT="${DEST_ROOT:-/opt/company-agent}"
HERMES_HOME="${HERMES_HOME:-/home/<service-user>/.hermes}"
VPS_HERMES_HOME="${VPS_HERMES_HOME:-${HOME}/.hermes}"
VPS_WEBUI_RUNTIME="${VPS_WEBUI_RUNTIME:-${DEST_ROOT}/webui/runtime}"
VPS_SYSTEMD_USER="${VPS_SYSTEMD_USER:-${HOME}/.config/systemd/user}"
PI_SYSTEMD_USER="${PI_SYSTEMD_USER:-${HERMES_HOME%/.*}/.config/systemd/user}"
HERMES_RUNTIME_REPO="${HERMES_RUNTIME_REPO:-git@github.com:<GITHUB_ORG>/hermes-agent-platform.git}"

RSYNC_FLAGS=(-aP)
if [[ "${MODE}" == "dry-run" ]]; then
  RSYNC_FLAGS+=(--dry-run)
fi

usage() {
  cat <<'EOF'
migrate-from-pi.sh — copy a one-host appliance onto this VPS.

Usage:
  bash scripts/migrate-from-pi.sh [--dry-run|--apply] <pi-host> [remote-user]

Defaults: --dry-run

Required:
  1. SSH access from this VPS to the old host (key auth).
  2. D050 reviewed: which old profiles map to employee-a/b/c / automation.
  3. Destination user and disk encryption already in place (INSTALL.md).
  4. GitHub access to clone <GITHUB_ORG>/hermes-agent-platform (or
     accept the rsync fallback of the live fork).

Environment overrides:
  DEST_ROOT=/opt/company-agent
  HERMES_HOME=/home/<service-user>/.hermes     # source on the old host
  VPS_HERMES_HOME=$HOME/.hermes                # destination on the VPS
  VPS_WEBUI_RUNTIME=$DEST_ROOT/webui/runtime
  VPS_SYSTEMD_USER=$HOME/.config/systemd/user
  PI_SYSTEMD_USER=/home/<service-user>/.config/systemd/user
  HERMES_RUNTIME_REPO=git@github.com:<GITHUB_ORG>/hermes-agent-platform.git

Example:
  DEST_ROOT=/opt/company-agent \
  HERMES_HOME=/home/<service-user>/.hermes \
  bash scripts/migrate-from-pi.sh [--dry-run|--apply] <pi-host> <remote-user>

Transfer list (what this script covers)
  RSYNC (read-only source → VPS):
    <hermes-home>/profiles/            →  $VPS_HERMES_HOME/profiles/
      (excludes per-profile .env and auth.json — those are OOB)
    <hermes-home>/state.db*            →  $VPS_HERMES_HOME/
    <hermes-home>/cron/                →  $VPS_HERMES_HOME/cron/
    <hermes-home>/gateway-starts.log   →  $VPS_HERMES_HOME/
    <hermes-home>/*.yaml               →  $VPS_HERMES_HOME/
      (config.yaml is NOT overwritten — sidecar config.yaml.from-pi)
    <remote>:/opt/company-agent/       →  $DEST_ROOT/  (if that tree exists)
    webui/runtime/*                    →  $VPS_WEBUI_RUNTIME/ (if present)
    plugins/dashboard_auth/company/    →  same fork path (fallback)
    hermes_cli/web_dist/               →  same path (or rebuild)
    ~/.config/systemd/user/hermes-desktop-web.service
    ~/.config/systemd/user/hermes-serve.service
    (hermes-dashboard.service is retired — not enabled)

  CLONE (preferred) or RSYNC fallback:
    <GITHUB_ORG>/hermes-agent-platform →  $VPS_HERMES_HOME/hermes-agent

  OUT OF BAND (documented steps only; chmod 0600; never git):
    <hermes-home>/dashboard-users.json
    <hermes-home>/notion-pat.env
    dashboard.company_auth.secret
      (from config.yaml or HERMES_DASHBOARD_COMPANY_AUTH_SECRET in .env)
    <hermes-home>/profiles/*/.env
    <hermes-home>/profiles/*/auth.json
    <hermes-home>/.env
    repo .env and infra/.env if present

What this never copies into git, and never treats as a secret bus:
  live tokens you have not rotated
  provider API keys
  ~/.hermes/dashboard-users.json
  ~/.hermes/notion-pat.env
  dashboard.company_auth.secret
  per-profile .env / auth.json
  another user's private profile into automation

After rsync:
  - merge dashboard.company_auth.* into the live config.yaml
    (do not overwrite the whole file blindly)
  - rotate every shared secret the old host could use
  - create missing employee-* profiles rather than renaming in place
  - keep automation as a service identity (spec 15.3)
  - rewrite hermes-desktop-web / hermes-serve unit paths for the VPS user;
    then systemctl --user enable + linger
  - do NOT enable hermes-dashboard.service (retired; browser UI is
    hermes-desktop-web on :9121)
  - run services tests and first-run checks (see docs/MIGRATION-VPS.md)
  - only then point DNS / gateway at the VPS
EOF
}

if [[ -z "${PI_HOST}" || "${PI_HOST}" == "<pi-host>" ]]; then
  usage
  exit 1
fi

SRC="${REMOTE_USER}@${PI_HOST}"

mkdir -p "${VPS_HERMES_HOME}/profiles" "${VPS_HERMES_HOME}/cron" \
  "${VPS_WEBUI_RUNTIME}" "${DEST_ROOT}" \
  "${VPS_HERMES_HOME}/hermes-agent/plugins/dashboard_auth/company" \
  "${VPS_HERMES_HOME}/hermes-agent/hermes_cli/web_dist" \
  "${VPS_SYSTEMD_USER}"

echo "mode=${MODE}  source=${SRC}  dest_hermes=${VPS_HERMES_HOME}"
echo

echo "== profiles (excluding per-profile .env / auth.json) =="
rsync "${RSYNC_FLAGS[@]}" \
  --exclude='.env' --exclude='auth.json' \
  "${SRC}:${HERMES_HOME}/profiles/" \
  "${VPS_HERMES_HOME}/profiles/" || true

echo
echo "== state.db (+ sidecars) =="
rsync "${RSYNC_FLAGS[@]}" \
  "${SRC}:${HERMES_HOME}/state.db" \
  "${SRC}:${HERMES_HOME}/state.db-wal" \
  "${SRC}:${HERMES_HOME}/state.db-shm" \
  "${VPS_HERMES_HOME}/" || true

echo
echo "== cron =="
rsync "${RSYNC_FLAGS[@]}" \
  "${SRC}:${HERMES_HOME}/cron/" \
  "${VPS_HERMES_HOME}/cron/" || true

echo
echo "== gateway-starts.log =="
rsync "${RSYNC_FLAGS[@]}" \
  "${SRC}:${HERMES_HOME}/gateway-starts.log" \
  "${VPS_HERMES_HOME}/" || true

echo
echo "== hermes yaml config (config.yaml is sidecar, not overwrite) =="
rsync "${RSYNC_FLAGS[@]}" \
  --exclude='config.yaml' \
  --include='*.yaml' --include='*.yml' --exclude='*' \
  "${SRC}:${HERMES_HOME}/" \
  "${VPS_HERMES_HOME}/" || true
rsync "${RSYNC_FLAGS[@]}" \
  "${SRC}:${HERMES_HOME}/config.yaml" \
  "${VPS_HERMES_HOME}/config.yaml.from-pi" || true
echo "WARNING: do not overwrite live config.yaml blindly."
echo "  Merge dashboard.company_auth.* (and other dashboard.* keys) from"
echo "  ${VPS_HERMES_HOME}/config.yaml.from-pi into the live file."
echo "  Typical keys:"
echo "    dashboard.company_auth.users_file: ${VPS_HERMES_HOME}/dashboard-users.json"
echo "    dashboard.company_auth.secret:     <paste OUT OF BAND — see below>"

echo
echo "== DEST_ROOT tree (if present on the old host) =="
rsync "${RSYNC_FLAGS[@]}" \
  "${SRC}:${DEST_ROOT}/" \
  "${DEST_ROOT}/" || true

echo
echo "== webui runtime (if present) =="
rsync "${RSYNC_FLAGS[@]}" \
  "${SRC}:${DEST_ROOT}/webui/runtime/" \
  "${VPS_WEBUI_RUNTIME}/" || true

echo
echo "== hermes-agent-platform runtime (clone preferred, rsync fallback) =="
echo "Preferred: clone ${HERMES_RUNTIME_REPO}"
echo "  into ${VPS_HERMES_HOME}/hermes-agent so the forked runtime"
echo "  (company DashboardAuthProvider, desktop-web, serve) comes along."
if [[ -d "${VPS_HERMES_HOME}/hermes-agent/.git" ]]; then
  echo "Runtime repo already present at ${VPS_HERMES_HOME}/hermes-agent"
  if [[ "${MODE}" == "apply" ]]; then
    git -C "${VPS_HERMES_HOME}/hermes-agent" pull --ff-only || \
      echo "WARNING: git pull failed — review remotes, then rsync fallback below."
  else
    echo "dry-run: would git pull --ff-only in ${VPS_HERMES_HOME}/hermes-agent"
  fi
elif [[ "${MODE}" == "apply" ]]; then
  if git clone "${HERMES_RUNTIME_REPO}" "${VPS_HERMES_HOME}/hermes-agent"; then
    echo "Cloned runtime fork."
  else
    echo "WARNING: clone failed (private repo / no deploy key)."
    echo "  Falling back to rsync of the live fork (excludes venv/node_modules)."
    rsync "${RSYNC_FLAGS[@]}" \
      --exclude='.venv/' --exclude='node_modules/' --exclude='__pycache__/' \
      "${SRC}:${HERMES_HOME}/hermes-agent/" \
      "${VPS_HERMES_HOME}/hermes-agent/" || true
  fi
else
  echo "dry-run: would git clone ${HERMES_RUNTIME_REPO} ${VPS_HERMES_HOME}/hermes-agent"
  echo "dry-run: rsync fallback would copy ${SRC}:${HERMES_HOME}/hermes-agent/"
fi

echo
echo "== company DashboardAuthProvider plugin =="
echo "Prefer: the clone/pull above already contains"
echo "  plugins/dashboard_auth/company/  on ${VPS_HERMES_HOME}/hermes-agent/"
echo "Fallback rsync (same fork path; excludes __pycache__):"
rsync "${RSYNC_FLAGS[@]}" \
  --exclude='__pycache__/' \
  "${SRC}:${HERMES_HOME}/hermes-agent/plugins/dashboard_auth/company/" \
  "${VPS_HERMES_HOME}/hermes-agent/plugins/dashboard_auth/company/" || true

echo
echo "== hermes_cli/web_dist (built web UI) =="
echo "If the VPS has node, prefer rebuilding instead of copying a Pi build:"
echo "  cd ${VPS_HERMES_HOME}/hermes-agent && npm run build"
echo "  # or run hermes dashboard / desktop-web without --skip-build once"
echo "Fallback rsync of the built tree:"
rsync "${RSYNC_FLAGS[@]}" \
  "${SRC}:${HERMES_HOME}/hermes-agent/hermes_cli/web_dist/" \
  "${VPS_HERMES_HOME}/hermes-agent/hermes_cli/web_dist/" || true

echo
echo "== systemd user units (desktop-web :9121 + serve :9120) =="
echo "hermes-dashboard.service is retired. Browser UI is hermes-desktop-web."
rsync "${RSYNC_FLAGS[@]}" \
  "${SRC}:${PI_SYSTEMD_USER}/hermes-desktop-web.service" \
  "${SRC}:${PI_SYSTEMD_USER}/hermes-serve.service" \
  "${VPS_SYSTEMD_USER}/" || true
echo "After apply: rewrite ExecStart/HOME/PATH/EnvironmentFile for the VPS user, then:"
echo "  systemctl --user daemon-reload"
echo "  systemctl --user enable --now hermes-desktop-web.service hermes-serve.service"
echo "  loginctl enable-linger \"\$USER\""
echo "Do not enable hermes-dashboard.service."

echo
echo "== OUT OF BAND — dashboard-users.json (0600, never git) =="
echo "Per-person dashboard password store. Transfer with scp, chmod 0600:"
echo "  scp ${SRC}:${HERMES_HOME}/dashboard-users.json \\"
echo "      ${VPS_HERMES_HOME}/dashboard-users.json"
echo "  chmod 0600 ${VPS_HERMES_HOME}/dashboard-users.json"
echo "Then point dashboard.company_auth.users_file at that path."

echo
echo "== OUT OF BAND — notion-pat.env (0600, never git) =="
echo "Hermes serve EnvironmentFile. Transfer with scp, chmod 0600:"
echo "  scp ${SRC}:${HERMES_HOME}/notion-pat.env \\"
echo "      ${VPS_HERMES_HOME}/notion-pat.env"
echo "  chmod 0600 ${VPS_HERMES_HOME}/notion-pat.env"
echo "Rewrite EnvironmentFile= in hermes-serve.service if the home path changed."

echo
echo "== OUT OF BAND — dashboard.company_auth.secret =="
echo "Capture on the old host (operator machine; do not paste into git/tickets):"
echo "  python3 -c \"import yaml; c=yaml.safe_load(open('${HERMES_HOME}/config.yaml')); print(c['dashboard']['company_auth']['secret'])\""
echo "  grep '^HERMES_DASHBOARD_COMPANY_AUTH_SECRET=' ${HERMES_HOME}/.env"
echo "On the VPS, set the SAME value so existing sessions survive, then rotate:"
echo "  hermes config set dashboard.company_auth.secret '<value>'"
echo "  chmod 0600 ${VPS_HERMES_HOME}/.env ${VPS_HERMES_HOME}/config.yaml"

echo
echo "== OUT OF BAND — per-profile .env / auth.json =="
echo "Profiles were rsynced without .env and auth.json. Copy each needed profile:"
echo "  for p in default employee-a employee-b employee-c automation; do"
echo "    scp ${SRC}:${HERMES_HOME}/profiles/\$p/.env \\"
echo "        ${VPS_HERMES_HOME}/profiles/\$p/.env 2>/dev/null || true"
echo "    scp ${SRC}:${HERMES_HOME}/profiles/\$p/auth.json \\"
echo "        ${VPS_HERMES_HOME}/profiles/\$p/auth.json 2>/dev/null || true"
echo "    chmod 0600 ${VPS_HERMES_HOME}/profiles/\$p/.env \\"
echo "               ${VPS_HERMES_HOME}/profiles/\$p/auth.json 2>/dev/null || true"
echo "  done"
echo "Also copy the host Hermes .env and repo env files if you still need them:"
echo "  scp ${SRC}:${HERMES_HOME}/.env ${VPS_HERMES_HOME}/.env"
echo "  scp ${SRC}:${DEST_ROOT}/.env ${DEST_ROOT}/.env"
echo "  scp ${SRC}:${DEST_ROOT}/infra/.env ${DEST_ROOT}/infra/.env"
echo "Rotate every secret the old host could still use after cutover."

echo
if [[ "${MODE}" == "dry-run" ]]; then
  echo "Dry-run only. Re-run with --apply after reviewing the file list"
  echo "and D050 mapping. Then transfer live credentials OUT OF BAND"
  echo "(dashboard-users.json, notion-pat.env, auth secret, per-profile"
  echo ".env/auth.json) and rotate every secret."
else
  echo "Apply finished. Complete the OUT OF BAND steps above, merge"
  echo "dashboard.* into config.yaml, install the runtime venv, then"
  echo "follow docs/MIGRATION-VPS.md. Do not point DNS at this VPS"
  echo "until first-run checks pass."
fi
