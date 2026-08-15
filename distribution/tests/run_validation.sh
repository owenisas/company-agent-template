#!/usr/bin/env bash
# Phase 1a validation. Spec 16 / 21.2 (schema, secret scan, required files).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
FAIL=0

note() { printf '%s\n' "$*"; }
pass() { printf 'PASS  %s\n' "$*"; }
fail() { printf 'FAIL  %s\n' "$*"; FAIL=1; }

note "=== Phase 1a validation ==="
HERMES_VER="$(set +o pipefail; hermes --version 2>/dev/null | awk 'NR==1{print; exit}')"
note "host: $(hostname)  hermes: ${HERMES_VER:-unavailable}"
note

note "--- (a) config.yaml keys vs installed Hermes ---"
KEYS=(
  terminal.backend
  terminal.home_mode
  terminal.cwd
  terminal.timeout
  terminal.env_passthrough
  terminal.docker_image
  terminal.docker_mount_cwd_to_workspace
  terminal.container_cpu
  terminal.container_memory
  terminal.container_disk
  terminal.container_persistent
  approvals.timeout
  approvals.mode
  memory.memory_enabled
  memory.user_profile_enabled
  memory.write_approval
  skills.write_approval
  plugins.enabled
  security.redact_secrets
  security.allow_lazy_installs
  mcp_servers
)
if ! command -v hermes >/dev/null 2>&1; then
  fail "hermes not on PATH"
else
  for k in "${KEYS[@]}"; do
    if hermes config get "$k" >/dev/null 2>&1; then
      pass "hermes config get $k"
    else
      fail "hermes config get $k"
    fi
  done
  if python3 - <<'PY'
import sys
from pathlib import Path
try:
    import yaml
except ImportError:
    sys.exit(2)
cfg = yaml.safe_load(Path("config.yaml").read_text())
assert cfg["terminal"]["backend"] == "docker"
assert cfg["memory"]["write_approval"] is True
assert cfg["skills"]["write_approval"] is True
assert cfg["security"]["redact_secrets"] is True
assert "mcp_servers" in cfg
print("distribution config.yaml required values present")
PY
  then
    pass "distribution config.yaml required values"
  else
    fail "distribution config.yaml required values"
  fi
fi

note
note "--- (b) git diff --check ---"
if git diff --check && git diff --cached --check; then
  pass "git diff --check"
else
  fail "git diff --check"
fi

note
note "--- (c) secret scan ---"
# Patterns from the Phase 1a brief. Assignment-like values fail.
# Bare words (token, secret) in policy docs are reported as INFO only.
SCAN_FILE="$(mktemp)"
trap 'rm -f "$SCAN_FILE"' EXIT
rg -n -I \
  -e 'api[_-]?key' \
  -e 'token' \
  -e 'password' \
  -e 'secret' \
  -e 'BEGIN.*PRIVATE KEY' \
  -e 'crsr_' \
  -e 'sk-' \
  -e 'ghp_' \
  --glob '!.git/**' \
  --glob '!tests/VALIDATION-1a.txt' \
  --glob '!scripts/_generate_phase1a_content.py' \
  . >"$SCAN_FILE" || true

python3 - "$SCAN_FILE" <<'PY'
import re, sys
from pathlib import Path
raw = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
lines = [ln for ln in raw.splitlines() if ln.strip()]
value_fail = []
info = []
# Real-looking assignments / PEM / product prefixes.
fail_re = re.compile(
    r"(BEGIN ([A-Z ]+)?PRIVATE KEY"
    r"|crsr_[A-Za-z0-9]{8,}"
    r"|ghp_[A-Za-z0-9]{20,}"
    r"|sk-[A-Za-z0-9]{16,}"
    r"|(?:api[_-]?key|password|secret|token)\s*[:=]\s*['\"][^'\"$\{\}<][^'\"]{8,}['\"])",
    re.I,
)
placeholder_re = re.compile(r"(TODO|EXAMPLE|<\w+>|\$\{[A-Z0-9_]+\})")
for ln in lines:
    if fail_re.search(ln) and not placeholder_re.search(ln):
        value_fail.append(ln)
    else:
        info.append(ln)
print(f"pattern_hits={len(lines)} value_failures={len(value_fail)} placeholder_or_docs={len(info)}")
if value_fail:
    print("VALUE FAILURES:")
    for ln in value_fail[:50]:
        print(ln)
    sys.exit(1)
print("no real credential values detected")
PY
if [[ $? -eq 0 ]]; then
  pass "secret scan (no credential values)"
else
  fail "secret scan found credential-like values"
fi

note
note "--- (d) distribution.yaml parses ---"
if python3 - <<'PY'
import sys
from pathlib import Path
import yaml
p = Path("distribution.yaml")
data = yaml.safe_load(p.read_text())
assert data["name"] == "<company>"
assert data["version"] == "0.1.0"
assert data["hermes_requires"] == ">=0.20.1"
assert "env_requires" in data and "distribution_owned" in data
print("ok", data["name"], data["version"])
PY
then
  pass "distribution.yaml parses"
else
  fail "distribution.yaml parse"
fi

note
note "--- (e) distribution_owned paths exist ---"
if python3 - <<'PY'
import sys
from pathlib import Path
import yaml
owned = yaml.safe_load(Path("distribution.yaml").read_text())["distribution_owned"]
missing = []
for item in owned:
    path = Path(item)
    if not path.exists():
        missing.append(item)
if missing:
    print("missing:", ", ".join(missing))
    sys.exit(1)
print("all distribution_owned paths exist")
PY
then
  pass "distribution_owned paths"
else
  fail "distribution_owned paths"
fi

note
note "--- (f) release manifest integrity (spec 36.6) ---"
if ./scripts/verify-release.sh manifests/company-agent-v0.1.0.yaml .; then
  pass "verify-release.sh"
else
  fail "verify-release.sh"
fi

note
if [[ "$FAIL" -eq 0 ]]; then
  note "VERDICT: PASS"
  exit 0
fi
note "VERDICT: FAIL"
exit 1
