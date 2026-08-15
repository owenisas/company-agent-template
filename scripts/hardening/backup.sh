#!/usr/bin/env bash
# Phase 5 backup scaffold (spec 31.3).
# Encrypt locally; copy off-host only when BACKUP_OFFHOST is set (D033).
# Fails closed on dump/encrypt/copy errors. Prints no secret values.
set -euo pipefail

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
HERMES_HOME="${HERMES_HOME:-${HOME}/.hermes}"
BACKUP_ROOT="${BACKUP_ROOT:-/var/backups/company-agent}"
OUT="${BACKUP_ROOT}/${STAMP}"
NOTION_PAT_ENV="${NOTION_PAT_ENV:-${HERMES_HOME}/secrets/notion-pat.env}"
COMPANY_REPOS_DIR="${COMPANY_REPOS_DIR:-${HOME}/workspace}"
COMPOSE_DIR="${COMPOSE_DIR:-}"
POSTGRES_USER="${POSTGRES_USER:-company_agent}"
POSTGRES_DB="${POSTGRES_DB:-company_agent}"
BACKUP_AGE_RECIPIENT="${BACKUP_AGE_RECIPIENT:-}"
BACKUP_OFFHOST="${BACKUP_OFFHOST:-}"

umask 077
mkdir -p "${OUT}/postgres" "${OUT}/profiles" "${OUT}/config" "${OUT}/repos" "${OUT}/audit"

log() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >&2; }

fail() {
  log "ERROR: $*"
  exit 1
}

# --- Hermes profiles ---
if [[ -d "${HERMES_HOME}/profiles" ]]; then
  tar -C "${HERMES_HOME}" -cf "${OUT}/profiles/profiles.tar" profiles
else
  log "WARN: no profiles dir at ${HERMES_HOME}/profiles"
fi

# --- Dashboard users + Notion PAT path (file if present; never cat) ---
if [[ -f "${HERMES_HOME}/dashboard-users.json" ]]; then
  cp -a "${HERMES_HOME}/dashboard-users.json" "${OUT}/config/dashboard-users.json"
fi
if [[ -f "${NOTION_PAT_ENV}" ]]; then
  cp -a "${NOTION_PAT_ENV}" "${OUT}/config/notion-pat.env"
fi

# --- Git mirrors (bundles; remotes are not enough) ---
if [[ -d "${COMPANY_REPOS_DIR}" ]]; then
  while IFS= read -r -d '' gitdir; do
    repo="$(dirname "${gitdir}")"
    name="$(basename "${repo}")"
    if git -C "${repo}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
      git -C "${repo}" bundle create "${OUT}/repos/${name}.bundle" --all
    fi
  done < <(find "${COMPANY_REPOS_DIR}" -mindepth 2 -maxdepth 3 -type d -name .git -print0 2>/dev/null || true)
fi

# --- PostgreSQL logical dump (optional; skip if compose not configured) ---
if [[ -n "${COMPOSE_DIR}" && -f "${COMPOSE_DIR}/compose.yaml" ]]; then
  if command -v docker >/dev/null 2>&1; then
    (
      cd "${COMPOSE_DIR}"
      docker compose exec -T postgres \
        pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
        --format=custom --no-owner --no-privileges
    ) > "${OUT}/postgres/${POSTGRES_DB}.dump" \
      || fail "pg_dump failed"
  else
    fail "COMPOSE_DIR set but docker not found"
  fi
else
  log "WARN: COMPOSE_DIR unset or compose.yaml missing; skipping postgres"
fi

# --- Checksums ---
(
  cd "${OUT}"
  find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
) > "${OUT}/SHA256SUMS"

# --- Encrypt (age) when a recipient is configured ---
BUNDLE="${BACKUP_ROOT}/${STAMP}.tar"
tar -C "${BACKUP_ROOT}" -cf "${BUNDLE}" "${STAMP}"

if [[ -n "${BACKUP_AGE_RECIPIENT}" ]]; then
  command -v age >/dev/null 2>&1 || fail "age not installed; cannot encrypt"
  age -r "${BACKUP_AGE_RECIPIENT}" -o "${BUNDLE}.age" "${BUNDLE}" \
    || fail "age encrypt failed"
  rm -f "${BUNDLE}"
  ARTIFACT="${BUNDLE}.age"
else
  log "WARN: BACKUP_AGE_RECIPIENT unset; local tar is plaintext under ${BACKUP_ROOT}"
  ARTIFACT="${BUNDLE}"
fi

# --- Off-host copy (D033). Fail closed if the operator asked for it and it fails. ---
if [[ -n "${BACKUP_OFFHOST}" ]]; then
  case "${BACKUP_OFFHOST}" in
    */ | *:*)
      scp -q "${ARTIFACT}" "${BACKUP_OFFHOST}" || fail "off-host copy failed"
      ;;
    *)
      mkdir -p "${BACKUP_OFFHOST}"
      cp -a "${ARTIFACT}" "${BACKUP_OFFHOST}/" || fail "off-host copy failed"
      ;;
  esac
  log "copied artifact to off-host target (path redacted)"
else
  log "WARN: BACKUP_OFFHOST unset (TODO D033); DR is not satisfied"
fi

log "backup complete stamp=${STAMP}"
printf '%s\n' "${OUT}"
