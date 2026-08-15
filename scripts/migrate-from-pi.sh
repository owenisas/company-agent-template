#!/usr/bin/env bash
# Move a one-host Pi (or other appliance) deployment onto a VPS.
# Generic helper. Review every path before running. Does not invent a
# profile mapping (D050).
#
# Usage (on the VPS, as an admin):
#   bash scripts/migrate-from-pi.sh [--dry-run|--apply] <pi-host> [remote-user]
#
# Default is --dry-run. Credentials, dashboard-users.json, PEMs, and bot
# tokens are transferred OUT OF BAND — never via git, never by this
# script inventing a secret channel.
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
# Source Hermes home on the old host (override).
HERMES_HOME="${HERMES_HOME:-/home/<service-user>/.hermes}"
# Destination Hermes home on the VPS (override if the VPS user differs).
VPS_HERMES_HOME="${VPS_HERMES_HOME:-${HOME}/.hermes}"
VPS_SYSTEMD_USER="${VPS_SYSTEMD_USER:-${HOME}/.config/systemd/user}"
PI_SYSTEMD_USER="${PI_SYSTEMD_USER:-${HERMES_HOME%/.*}/.config/systemd/user}"
# If HERMES_HOME is /home/<user>/.hermes, default systemd dir is
# /home/<user>/.config/systemd/user. Override PI_SYSTEMD_USER when that
# heuristic is wrong.

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

Environment overrides:
  DEST_ROOT=/opt/company-agent
  HERMES_HOME=/home/<service-user>/.hermes     # source on the old host
  VPS_HERMES_HOME=$HOME/.hermes                # destination on the VPS
  VPS_SYSTEMD_USER=$HOME/.config/systemd/user
  PI_SYSTEMD_USER=/home/<service-user>/.config/systemd/user

Example:
  DEST_ROOT=/opt/company-agent \
  HERMES_HOME=/home/<service-user>/.hermes \
  bash scripts/migrate-from-pi.sh [--dry-run|--apply] <pi-host> <remote-user>

What this rsyncs (read-only source):
  <remote>:<hermes-home>/profiles/   ->  $VPS_HERMES_HOME/profiles/
  <remote>:<hermes-home>/*.yaml      ->  $VPS_HERMES_HOME/   (config only;
                                     config.yaml is NOT overwritten —
                                     sidecar config.yaml.from-pi)
  <remote>:/opt/company-agent/       ->  $DEST_ROOT/     (if that tree exists)
  <remote>:<hermes-home>/hermes-agent/plugins/dashboard_auth/company/
                                     ->  same fork path on the VPS
                                     (prefer git pull of the hermes-agent
                                     fork that contains this plugin)
  <remote>:<hermes-home>/hermes-agent/hermes_cli/web_dist/
                                     ->  same path (or rebuild on VPS)
  <remote>:~/.config/systemd/user/hermes-dashboard.service
  <remote>:~/.config/systemd/user/hermes-serve.service

What this never copies into git, and never treats as a secret bus:
  live tokens you have not rotated
  provider API keys
  ~/.hermes/dashboard-users.json   (per-person dashboard passwords)
  another user's private profile into automation

Out-of-band credential transfer (operator, not this script):
  - provider tokens / OAuth
  - ~/.hermes/dashboard-users.json  (scp; chmod 0600; NEVER git)

After rsync:
  - merge dashboard.company_auth.* into the live config.yaml
    (do not overwrite the whole file blindly)
  - rotate every shared secret the old host could use
  - create missing employee-* profiles rather than renaming in place
  - keep automation as a service identity (spec 15.3)
  - rewrite hermes-dashboard / hermes-serve unit paths for the VPS user;
    then systemctl --user enable + linger
  - run services tests and first-run checks in INSTALL.md
  - only then point DNS / gateway at the VPS
EOF
}

if [[ -z "${PI_HOST}" || "${PI_HOST}" == "<pi-host>" ]]; then
  usage
  exit 1
fi

SRC="${REMOTE_USER}@${PI_HOST}"

mkdir -p "${VPS_HERMES_HOME}/profiles" "${DEST_ROOT}" \
  "${VPS_HERMES_HOME}/hermes-agent/plugins/dashboard_auth/company" \
  "${VPS_HERMES_HOME}/hermes-agent/hermes_cli/web_dist" \
  "${VPS_SYSTEMD_USER}"

echo "mode=${MODE}  source=${SRC}  dest_hermes=${VPS_HERMES_HOME}"
echo

echo "== profiles =="
rsync "${RSYNC_FLAGS[@]}" \
  "${SRC}:${HERMES_HOME}/profiles/" \
  "${VPS_HERMES_HOME}/profiles/" || true

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
echo "    dashboard.company_auth.users_file: <VPS_HERMES_HOME>/dashboard-users.json"

echo
echo "== DEST_ROOT tree (if present on the old host) =="
rsync "${RSYNC_FLAGS[@]}" \
  "${SRC}:${DEST_ROOT}/" \
  "${DEST_ROOT}/" || true

echo
echo "== company DashboardAuthProvider plugin =="
echo "Prefer: git pull the hermes-agent fork that already contains"
echo "  plugins/dashboard_auth/company/  onto ${VPS_HERMES_HOME}/hermes-agent/"
echo "Fallback rsync (same fork path; excludes __pycache__):"
rsync "${RSYNC_FLAGS[@]}" \
  --exclude='__pycache__/' \
  "${SRC}:${HERMES_HOME}/hermes-agent/plugins/dashboard_auth/company/" \
  "${VPS_HERMES_HOME}/hermes-agent/plugins/dashboard_auth/company/" || true

echo
echo "== hermes_cli/web_dist (built web UI) =="
echo "If the VPS has node, prefer rebuilding instead of copying a Pi build:"
echo "  cd ${VPS_HERMES_HOME}/hermes-agent && npm run build"
echo "  # or run hermes dashboard without --skip-build once"
echo "Fallback rsync of the built tree:"
rsync "${RSYNC_FLAGS[@]}" \
  "${SRC}:${HERMES_HOME}/hermes-agent/hermes_cli/web_dist/" \
  "${VPS_HERMES_HOME}/hermes-agent/hermes_cli/web_dist/" || true

echo
echo "== systemd user units (dashboard + serve) =="
rsync "${RSYNC_FLAGS[@]}" \
  "${SRC}:${PI_SYSTEMD_USER}/hermes-dashboard.service" \
  "${SRC}:${PI_SYSTEMD_USER}/hermes-serve.service" \
  "${VPS_SYSTEMD_USER}/" || true
echo "After apply: rewrite ExecStart/HOME/PATH for the VPS user, then:"
echo "  systemctl --user daemon-reload"
echo "  systemctl --user enable --now hermes-dashboard.service hermes-serve.service"
echo "  loginctl enable-linger \"\$USER\""

echo
echo "== dashboard-users.json (OUT OF BAND — not rsynced, never git) =="
echo "WARNING: per-person dashboard password store. Transfer with scp,"
echo "chmod 0600, never commit:"
echo "  scp ${SRC}:${HERMES_HOME}/dashboard-users.json \\"
echo "      ${VPS_HERMES_HOME}/dashboard-users.json"
echo "  chmod 0600 ${VPS_HERMES_HOME}/dashboard-users.json"
echo "Then point dashboard.company_auth.users_file at that path."

echo
if [[ "${MODE}" == "dry-run" ]]; then
  echo "Dry-run only. Re-run with --apply after reviewing the file list"
  echo "and D050 mapping. Then transfer live credentials OUT OF BAND"
  echo "(including dashboard-users.json) and rotate every secret."
else
  echo "Apply finished. Rotate secrets out of band. scp dashboard-users.json"
  echo "and merge dashboard.* into config.yaml. Do not point DNS at this"
  echo "VPS until INSTALL.md first-run checks pass."
fi
