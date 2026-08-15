#!/usr/bin/env bash
# Move a one-host Pi (or other appliance) deployment onto a VPS.
# Generic helper. Review every path before running. Does not invent a
# profile mapping (D050).
#
# Usage (on the VPS, as an admin):
#   bash scripts/migrate-from-pi.sh <pi-host> [remote-user]
set -euo pipefail

PI_HOST="${1:-}"
REMOTE_USER="${2:-<remote-user>}"
DEST_ROOT="${DEST_ROOT:-/opt/company-agent}"
HERMES_HOME="${HERMES_HOME:-/home/<service-user>/.hermes}"

if [[ -z "${PI_HOST}" || "${PI_HOST}" == "<pi-host>" ]]; then
  cat <<'EOF'
migrate-from-pi.sh — copy a one-host appliance onto this VPS.

Required:
  1. SSH access from this VPS to the old host (key auth).
  2. D050 reviewed: which old profiles map to employee-a/b/c / automation.
  3. Destination user and disk encryption already in place (INSTALL.md).

Example:
  DEST_ROOT=/opt/company-agent \
  HERMES_HOME=/home/<service-user>/.hermes \
  bash scripts/migrate-from-pi.sh <pi-host> <remote-user>

What this rsyncs (read-only source):
  <remote>:<hermes-home>/profiles/   ->  $HERMES_HOME/profiles/
  <remote>:<hermes-home>/*.yaml      ->  $HERMES_HOME/   (config only)
  <remote>:/opt/company-agent/       ->  $DEST_ROOT/     (if that tree exists)

What this never copies:
  live tokens you have not rotated
  provider API keys into Git
  another user's private profile into automation

After rsync:
  - rotate every shared secret the old host could use
  - create missing employee-* profiles rather than renaming in place
  - keep automation as a service identity (spec 15.3)
  - run services tests and first-run checks in INSTALL.md
  - only then point DNS / gateway at the VPS
EOF
  exit 1
fi

mkdir -p "${HERMES_HOME}/profiles" "${DEST_ROOT}"

echo "rsync profiles from ${REMOTE_USER}@${PI_HOST} ..."
rsync -aP --dry-run \
  "${REMOTE_USER}@${PI_HOST}:${HERMES_HOME}/profiles/" \
  "${HERMES_HOME}/profiles/" || true

echo
echo "Dry-run only. Re-run with rsync -aP (no --dry-run) after reviewing"
echo "the file list and D050 mapping. Then rotate secrets."
