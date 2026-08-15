---
name: pull-request-delivery
description: Open a reviewable pull request from a task worktree.
required_environment_variables:
  - COMPANY_KB_TOKEN
---

# Pull Request Delivery

Domain: engineering. Spec 19.2 / 19.3. Safe defaults: read-only unless a
named approval skill is used. No credentials in this file.

## Use when

Use after tests pass in a task worktree and a reviewer path exists.

## Procedure

1. Confirm task ID, branch, test results, and stable path.
2. Push the task branch only to the approved remote.
3. Open a PR into testing (not main) unless a release owner directs otherwise.
4. Cite the test command and result in the PR body.
5. Do not merge protected branches.

## Safety

- Requires the user's GitHub identity, not a silent bot substitution (spec 15.6).
- No production deploy from this skill.
