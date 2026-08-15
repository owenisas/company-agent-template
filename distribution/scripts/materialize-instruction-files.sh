#!/usr/bin/env bash
# Copy spec 16.4 / 16.5 instruction files to the distribution root.
# Hermes blocks writes to SOUL.md / AGENTS.md from the agent session.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cp -f "$ROOT/docs/soul-baseline.md" "$ROOT/SOUL.md"
cp -f "$ROOT/docs/agents-baseline.md" "$ROOT/AGENTS.md"
chmod 0644 "$ROOT/SOUL.md" "$ROOT/AGENTS.md"
printf 'materialized SOUL.md and AGENTS.md\n'
