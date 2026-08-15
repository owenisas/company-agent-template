---
name: github-task-worktree
description: Create an isolated git worktree and branch for a named task.
required_environment_variables:
  - COMPANY_KB_TOKEN
---

# Github Task Worktree

Domain: engineering. Spec 19.2 / 19.3. Safe defaults: read-only unless a
named approval skill is used. No credentials in this file.

## Use when

Use before any executable code change (spec 16.5 rule 8).

## Procedure

1. Require a task ID and requesting user slug.
2. Run scripts/worktree.sh with user, task, repo, and base ref.
3. Confirm the destination is outside production profile directories.
4. Record branch, worktree path, and tests to run.
5. Do not push or merge from this skill.

## Safety

- No shared deploy keys in the worktree environment.
- Do not run against the live control-plane checkout.
- Protected-branch merge is out of scope.
