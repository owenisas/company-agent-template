#!/usr/bin/env bash
# Spec 36.5 worktree creation, adapted to this distribution repo.
# Default DEST stays under /srv/company-agent/worktrees unless overridden.
# TODO: confirm DEST root and whether /srv exists on the control-plane host (D031).
set -euo pipefail

USER_ID="${1:?user id required}"
TASK_ID="${2:?task id required}"
REPO="${3:?repository path required}"
BASE="${4:-origin/main}"
DEST_ROOT="${COMPANY_WORKTREE_ROOT:-/srv/company-agent/worktrees}"

SAFE_USER="$(printf '%s' "$USER_ID" | tr -cd 'a-zA-Z0-9._-')"
SAFE_TASK="$(printf '%s' "$TASK_ID" | tr -cd 'a-zA-Z0-9._-')"
BRANCH="agent/${SAFE_USER}/${SAFE_TASK}"
DEST="${DEST_ROOT}/${SAFE_USER}/${SAFE_TASK}"

[ -n "$SAFE_USER" ] && [ -n "$SAFE_TASK" ]
[ -d "$REPO" ]
mkdir -p "$(dirname "$DEST")"

git -C "$REPO" fetch --prune origin
git -C "$REPO" worktree add -b "$BRANCH" "$DEST" "$BASE"
printf '%s\n' "$DEST"
