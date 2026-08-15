# Runbook: code-release

Phase 4 §4490. Skills `github-task-worktree`, `pull-request-delivery`,
`release-promotion`. Specialists: `engineering.*`.
Companion: `runbooks/release-promotion.md` (channel promotion).
Normative: matrix §3 Deploy / Skill change,
`github.pull_request.create`, `github.protected_branch.merge`.

## When to use

A company code change that must land via worktree → PR → CI →
protected merge → release manifest. Not a host-shell hotfix.

## Inputs

- Requester and task id
- Target repo (D042 org still open)
- Risk class (skill text vs policy/plugin/security)
- Tests that must pass

## Steps

1. Identify requester. Load an engineering specialist. No production
   secret in the worktree.
2. Create an isolated worktree (`github-task-worktree`). Never edit
   the live VPS checkout in place for company code.
3. Implement, run offline tests, open a PR as the approved GitHub
   principal (`github.pull_request.create`, approval none for
   engineering).
4. CI + `tests/run_validation.sh` + `scripts/verify-release.sh`.
5. Protected merge is R3: `github.protected_branch.merge` →
   `approval: repository-protection`. Two reviewers when the change
   is policy/plugin/security (D017).
6. Promote `working` → `testing` → `stable` via
   `runbooks/release-promotion.md`. Automation MAY open the release
   PR; MUST NOT push `main` or apply production compose without
   approval.
7. Record SHAs, image digests, specialist overlay version, approvers.

## Approval gates

| Action | Tier | Gate |
|---|---|---|
| Open PR / comment | R1/R2 | Automatic for engineering |
| Merge protected branch | R3 | Repository protection + CODEOWNERS |
| Promote testing → stable | R3 | Two named release approvers — TODO **D017** |
| Apply production compose/digest | R3 | `agent-platform-admins` — TODO **D008/D015** |
| Privilege / secret-scope change | R3/R4 | Must not be done from this runbook |

## Outputs

- PR URL, CI status, merge SHA
- Release manifest update
- Rollback pointer (previous manifest)

## What must NEVER happen

- Commit or run model-generated commands on the VPS host
- Merge to `main` without protection
- Deploy a floating `latest` tag
- Self-approve a stable policy/plugin change as `company-automation`
- Ship a specialist overlay without the D041 pin
