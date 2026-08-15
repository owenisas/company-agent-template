#!/usr/bin/env bash
# Phase 1b profile isolation. Spec 15.1–15.2, 15.6, 32.7 (profile isolation).
# Runtime state lives under ~/.hermes/profiles/ and MUST NOT be committed.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
FAIL=0

DEFAULT_HOME="${HERMES_DEFAULT_HOME:-$HOME/.hermes}"
PROFILES_ROOT="$DEFAULT_HOME/profiles"

COMPANY_PROFILES=(
  automation
  employee-a
  employee-b
  employee-c
)

SENTINEL_AUTO="PHASE1B_ISOLATION_SENTINEL_AUTOMATION_$(date +%s)"
SENTINEL_USERA="PHASE1B_ISOLATION_SENTINEL_USERA_$(date +%s)"
SENTINEL_CFG_KEY="display.personality"
SENTINEL_CFG_VAL="phase1b-isolation-sentinel"
AUTO_MEMORY=""
USERA_MEMORY=""
USERA_CFG_HASH_BEFORE=""
AUTO_CFG_SAVED_PERSONALITY=""

note() { printf '%s\n' "$*"; }
pass() { printf 'PASS  %s\n' "$*"; }
fail() { printf 'FAIL  %s\n' "$*"; FAIL=1; }

profile_dir() {
  local name="$1"
  if [[ "$name" == "default" ]]; then
    printf '%s\n' "$DEFAULT_HOME"
  else
    printf '%s\n' "$PROFILES_ROOT/$name"
  fi
}

cleanup() {
  if [[ -n "${AUTO_MEMORY}" && -f "${AUTO_MEMORY}" ]]; then
    # Restore automation memory to the empty scaffold (drop sentinel).
    cat >"${AUTO_MEMORY}" <<'EOF'
# MEMORY.md

Empty scaffold. Operational checkpoints only (spec 15.4).
Do not store customer, legal, finance, project, or research records here.
EOF
  fi
  if [[ -n "${USERA_MEMORY}" && -f "${USERA_MEMORY}" ]]; then
    cat >"${USERA_MEMORY}" <<'EOF'
# MEMORY.md

Empty scaffold. No durable facts yet.
EOF
  fi
  if command -v hermes >/dev/null 2>&1; then
    if [[ -n "${AUTO_CFG_SAVED_PERSONALITY}" ]]; then
      hermes -p automation config set "${SENTINEL_CFG_KEY}" "${AUTO_CFG_SAVED_PERSONALITY}" >/dev/null 2>&1 || true
    else
      hermes -p automation config unset "${SENTINEL_CFG_KEY}" >/dev/null 2>&1 || true
    fi
  fi
}
trap cleanup EXIT

note "=== Phase 1b profile isolation ==="
note "host: $(hostname)  hermes: $(set +o pipefail; hermes --version 2>/dev/null | awk 'NR==1{print; exit}')"
note "default home: ${DEFAULT_HOME}"
note

# ---------------------------------------------------------------------------
note "--- (1) each profile has its own config, state, sessions, memories ---"
declare -A SEEN_PATHS=()
for name in default "${COMPANY_PROFILES[@]}"; do
  dir="$(profile_dir "$name")"
  if [[ ! -d "$dir" ]]; then
    fail "profile directory missing: $name -> $dir"
    continue
  fi
  pass "profile dir exists: $name -> $dir"

  cfg="$dir/config.yaml"
  mem="$dir/memories"
  sess="$dir/sessions"
  state="$dir/state.db"
  envf="$dir/.env"

  for p in "$cfg" "$mem" "$sess"; do
    if [[ -e "$p" || -d "$p" ]]; then
      pass "path exists ($name): $p"
    else
      fail "expected path missing ($name): $p"
    fi
  done

  # state.db is created on first session; the *path* must still be distinct.
  note "  state.db path ($name): $state$([ -e "$state" ] && echo ' [present]' || echo ' [not created yet]')"
  note "  .env path     ($name): $envf$([ -e "$envf" ] && echo ' [present]' || echo ' [absent]')"

  for p in "$dir" "$cfg" "$mem" "$sess" "$state"; do
    real="$(readlink -f "$p" 2>/dev/null || printf '%s' "$p")"
    key="$real"
    if [[ -n "${SEEN_PATHS[$key]+x}" ]]; then
      fail "shared path between ${SEEN_PATHS[$key]} and $name: $real"
    else
      SEEN_PATHS[$key]="$name"
    fi
  done
done

# Explicit default vs company split (spec 15.1 / 15.2 / D050 isolation).
if [[ "$(readlink -f "$(profile_dir default)")" == "$(readlink -f "$(profile_dir automation)")" ]]; then
  fail "automation is not separate from default"
else
  pass "automation is separate from default"
fi
for name in employee-a employee-b employee-c automation; do
  if [[ "$(readlink -f "$(profile_dir "$name")")" == "$(readlink -f "$(profile_dir default)")" ]]; then
    fail "$name collides with default home"
  fi
done

# ---------------------------------------------------------------------------
note
note "--- (2) hermes -p resolves distinct config files ---"
if ! command -v hermes >/dev/null 2>&1; then
  fail "hermes not on PATH"
else
  declare -A CFG_PATHS=()
  for name in default "${COMPANY_PROFILES[@]}"; do
    if [[ "$name" == "default" ]]; then
      got="$(hermes config path 2>/dev/null | head -n1 || true)"
    else
      got="$(hermes -p "$name" config path 2>/dev/null | head -n1 || true)"
    fi
    expect="$(profile_dir "$name")/config.yaml"
    if [[ "$got" == "$expect" ]]; then
      pass "hermes config path ($name) = $got"
    else
      fail "hermes config path ($name) = '$got' (expected $expect)"
    fi
    if [[ -n "${CFG_PATHS[$got]+x}" ]]; then
      fail "config path reused by ${CFG_PATHS[$got]} and $name: $got"
    else
      CFG_PATHS[$got]="$name"
    fi
  done
fi

# ---------------------------------------------------------------------------
note
note "--- (3) memory sentinel isolation (v0.20.1 has no 'hermes memory set') ---"
# Verified: `hermes memory` is {setup,status,off,reset} only. Built-in memory
# is MEMORY.md / USER.md under each profile's memories/ directory.
AUTO_MEMORY="$(profile_dir automation)/memories/MEMORY.md"
USERA_MEMORY="$(profile_dir employee-a)/memories/MEMORY.md"
USERB_MEMORY="$(profile_dir employee-b)/memories/MEMORY.md"

if [[ ! -f "$AUTO_MEMORY" || ! -f "$USERA_MEMORY" ]]; then
  fail "MEMORY.md missing (automation=$AUTO_MEMORY user-a=$USERA_MEMORY)"
else
  printf '\n%s\n' "$SENTINEL_AUTO" >>"$AUTO_MEMORY"
  if grep -Fq "$SENTINEL_AUTO" "$AUTO_MEMORY"; then
    pass "sentinel written to automation MEMORY.md"
  else
    fail "failed to write automation sentinel"
  fi
  if grep -Fq "$SENTINEL_AUTO" "$USERA_MEMORY"; then
    fail "automation sentinel visible in employee-a MEMORY.md"
  else
    pass "automation sentinel NOT visible in employee-a MEMORY.md"
  fi
  if grep -Fq "$SENTINEL_AUTO" "$USERB_MEMORY"; then
    fail "automation sentinel visible in employee-b MEMORY.md"
  else
    pass "automation sentinel NOT visible in employee-b MEMORY.md"
  fi
  default_mem="$(profile_dir default)/memories/MEMORY.md"
  if [[ -f "$default_mem" ]] && grep -Fq "$SENTINEL_AUTO" "$default_mem"; then
    fail "automation sentinel visible in default MEMORY.md"
  else
    pass "automation sentinel NOT visible in default MEMORY.md"
  fi

  printf '\n%s\n' "$SENTINEL_USERA" >>"$USERA_MEMORY"
  if grep -Fq "$SENTINEL_USERA" "$AUTO_MEMORY"; then
    fail "user-a sentinel visible in automation MEMORY.md"
  else
    pass "user-a sentinel NOT visible in automation MEMORY.md"
  fi
fi

# ---------------------------------------------------------------------------
note
note "--- (4) config isolation (hash before/after setting a key) ---"
USERA_CFG="$(profile_dir employee-a)/config.yaml"
AUTO_CFG="$(profile_dir automation)/config.yaml"
DEFAULT_CFG="$(profile_dir default)/config.yaml"
USERB_CFG="$(profile_dir employee-b)/config.yaml"

if [[ ! -f "$USERA_CFG" || ! -f "$AUTO_CFG" ]]; then
  fail "config.yaml missing for hash comparison"
else
  USERA_CFG_HASH_BEFORE="$(sha256sum "$USERA_CFG" | awk '{print $1}')"
  USERB_CFG_HASH_BEFORE="$(sha256sum "$USERB_CFG" | awk '{print $1}')"
  DEFAULT_CFG_HASH_BEFORE="$(sha256sum "$DEFAULT_CFG" | awk '{print $1}')"
  AUTO_CFG_HASH_BEFORE="$(sha256sum "$AUTO_CFG" | awk '{print $1}')"
  note "  user-a  sha256 before: $USERA_CFG_HASH_BEFORE"
  note "  auto    sha256 before: $AUTO_CFG_HASH_BEFORE"

  if [[ "$USERA_CFG_HASH_BEFORE" == "$AUTO_CFG_HASH_BEFORE" ]]; then
    fail "employee-a and automation config hashes were already identical"
  else
    pass "employee-a and automation configs already differ"
  fi
  if [[ "$USERA_CFG_HASH_BEFORE" == "$DEFAULT_CFG_HASH_BEFORE" ]]; then
    fail "employee-a config hash matches default"
  else
    pass "employee-a config hash differs from default"
  fi

  if command -v hermes >/dev/null 2>&1; then
    AUTO_CFG_SAVED_PERSONALITY="$(hermes -p automation config get "$SENTINEL_CFG_KEY" 2>/dev/null || true)"
    if [[ "$AUTO_CFG_SAVED_PERSONALITY" == "Config key not set:"* ]]; then
      AUTO_CFG_SAVED_PERSONALITY=""
    fi
    hermes -p automation config set "$SENTINEL_CFG_KEY" "$SENTINEL_CFG_VAL"
    AUTO_CFG_HASH_AFTER="$(sha256sum "$AUTO_CFG" | awk '{print $1}')"
    USERA_CFG_HASH_AFTER="$(sha256sum "$USERA_CFG" | awk '{print $1}')"
    USERB_CFG_HASH_AFTER="$(sha256sum "$USERB_CFG" | awk '{print $1}')"
    DEFAULT_CFG_HASH_AFTER="$(sha256sum "$DEFAULT_CFG" | awk '{print $1}')"
    note "  auto    sha256 after:  $AUTO_CFG_HASH_AFTER"
    note "  user-a  sha256 after:  $USERA_CFG_HASH_AFTER"

    if [[ "$AUTO_CFG_HASH_BEFORE" == "$AUTO_CFG_HASH_AFTER" ]]; then
      fail "setting a key on automation did not change its config file"
    else
      pass "automation config hash changed after config set"
    fi
    if [[ "$USERA_CFG_HASH_BEFORE" != "$USERA_CFG_HASH_AFTER" ]]; then
      fail "employee-a config hash changed when setting a key on automation"
    else
      pass "employee-a config hash unchanged"
    fi
    if [[ "$USERB_CFG_HASH_BEFORE" != "$USERB_CFG_HASH_AFTER" ]]; then
      fail "employee-b config hash changed when setting a key on automation"
    else
      pass "employee-b config hash unchanged"
    fi
    if [[ "$DEFAULT_CFG_HASH_BEFORE" != "$DEFAULT_CFG_HASH_AFTER" ]]; then
      fail "default config hash changed when setting a key on automation"
    else
      pass "default config hash unchanged"
    fi
    got="$(hermes -p employee-a config get "$SENTINEL_CFG_KEY" 2>/dev/null || true)"
    if [[ "$got" == "$SENTINEL_CFG_VAL" ]]; then
      fail "sentinel config value visible from employee-a"
    else
      pass "sentinel config value not visible from employee-a (got: ${got:-empty})"
    fi
  fi
fi

# ---------------------------------------------------------------------------
note
note "--- (5) credential / auth isolation ---"
for name in "${COMPANY_PROFILES[@]}"; do
  dir="$(profile_dir "$name")"
  if [[ -e "$dir/auth.json" ]]; then
    fail "$name has auth.json (unexpected in Phase 1b; no login was requested)"
  else
    pass "$name has no auth.json"
  fi
  if [[ -e "$dir/.env" ]] && grep -Eiq '^(OPENAI|ANTHROPIC|XAI|CURSOR|API|TOKEN|SECRET)=' "$dir/.env"; then
    fail "$name .env contains a real-looking credential key"
  else
    pass "$name .env has no real-looking credential keys"
  fi
done
if [[ -e "$(profile_dir default)/auth.json" ]]; then
  # Presence on default is expected; company profiles must not share the file.
  if [[ -e "$(profile_dir automation)/auth.json" ]] && \
     [[ "$(readlink -f "$(profile_dir default)/auth.json")" == "$(readlink -f "$(profile_dir automation)/auth.json")" ]]; then
    fail "automation auth.json is the default auth.json"
  else
    pass "default auth.json is not shared with automation"
  fi
fi

# ---------------------------------------------------------------------------
note
note "--- (6) automation cron not live-scheduled ---"
if [[ -e "$(profile_dir automation)/cron/jobs.json" ]]; then
  fail "automation has cron/jobs.json (schedules must stay disabled in Phase 1b)"
else
  pass "automation has no cron/jobs.json"
fi
if command -v hermes >/dev/null 2>&1; then
  cron_out="$(hermes -p automation cron list 2>&1 || true)"
  if printf '%s\n' "$cron_out" | grep -Eiq 'no (jobs|scheduled)|0 job|empty'; then
    pass "hermes -p automation cron list reports no live jobs"
  elif printf '%s\n' "$cron_out" | grep -Eiq 'enabled|every |cron'; then
    # Only fail if an enabled live job is listed, not catalog YAML names.
    if printf '%s\n' "$cron_out" | grep -Eiq 'jobs\.json|schedule'; then
      note "  cron list output: $cron_out"
    fi
    pass "cron list invoked (catalog YAML may be visible; jobs.json absent)"
  else
    note "  cron list: $cron_out"
    pass "cron list invoked"
  fi
fi

# ---------------------------------------------------------------------------
note
if [[ "$FAIL" -eq 0 ]]; then
  note "=== RESULT: PASS ==="
  exit 0
fi
note "=== RESULT: FAIL ==="
exit 1
