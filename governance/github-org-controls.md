# GitHub organization controls

**Company slug:** `<company>`
**Normative sources:** spec Sections 2, 5.7, 5.8, 8, 9.1–9.4, 12.2, 16.3, 33.5, 34 Phase 0, 38.2, 38.14
**Status:** Phase 0 baseline
**Owner of this document:** TODO: platform-ops owner / `agent-platform-admins`
**GitHub organization:** TODO: `<GITHUB_ORG>` (MUST be recorded before repositories are treated as production)

This file is the policy for GitHub org structure, teams, branch protection, required reviews, the three required repositories, and the no-secrets-in-git rule. Live GitHub settings MUST match this document once the org name is chosen. Until then, this file is binding policy for any local or remote Git use of `company-agent-platform`.

## 1. Organization structure (spec 9.1)

Create these **private** repositories:

```text
<GITHUB_ORG>/company-agent-distribution
<GITHUB_ORG>/company-agent-platform
<GITHUB_ORG>/company-knowledge-curated
```

`<GITHUB_ORG>` MAY equal the company slug `<company>` but MUST be an explicit decision (see `DECISIONS-NEEDED.md`). Optional post-pilot repositories (`company-agent-evals`, `company-agent-connectors`, `company-data-contracts`) MUST remain private and MUST reuse the teams in Section 2.

Do not give all three employees organization-owner rights. Keep at least two organization owners for account recovery, but use lower repository roles for normal work (spec 9.2).

| Org role | Humans | Notes |
|---|---|---|
| Organization owner | TODO: two named humans | Recovery only. MUST NOT be all three employees. |
| Billing / enterprise admin | TODO: | Out of agent scope |
| Outside collaborators | None by default | Adding one is an R3 privilege change |

## 2. Teams and permissions (spec 9.2)

Cross-reference `docs/governance/user-role-group-registry.md`.

| Team | Permission | Purpose | Members |
|---|---|---|---|
| `agent-platform-admins` | Maintain/Admin | Host, secrets, incident response, releases | TODO: |
| `agent-builders` | Write | Skills, plugins, runbooks, tests, platform code | TODO: |
| `agent-users` | Read | Install stable distribution and read approved docs | Authorized employees |
| `legal-approvers` | Triage/Read plus approval role | Contract/legal policy review | TODO: legal owner |
| `finance-approvers` | Triage/Read plus approval role | Payments and financial action approval | TODO: finance owner |

A person MAY belong to several teams. Machine identities (GitHub App / `automation` bot) MUST NOT be organization owners and SHOULD be limited to the least team permission that can open PRs and write allowed checks.

## 3. Branch policy (spec 8, 9.3)

| Branch | Purpose | Spec name |
|---|---|---|
| `main` | Stable production source | Stable branch (spec 8) |
| `testing` | Integrated pre-production source | Test branch (spec 8) |
| `feature/*` | Human feature work | Working |
| `agent/<user>/<task>` | Agent-created work | Working; `<user>` is an 11.3 slug or `automation` |
| `hotfix/*` | Urgent reviewed corrections | Promoted only through the same protections |

This working clone currently uses Git's default `master` branch because the repository has no remotes or commits yet. The first commit MAY land on `master`. Before the repository is published, operators MUST rename the default branch to `main` (`git branch -M main`) so local history matches this policy. Until that rename, `master` is a local bootstrap alias for `main` and MUST NOT be treated as a second stable line.

Protect `main` and `testing`:

- require pull requests;
- require at least one reviewer for `testing` and two for policy/plugin/security changes into `main`;
- one reviewer MAY suffice for low-risk skill text changes into `main` (spec 8);
- dismiss approvals when code changes;
- require status checks;
- require conversation resolution;
- block force pushes and branch deletion;
- require signed commits or verified GitHub identity where practical (TODO: whether signed commits are mandatory);
- require CODEOWNERS review for `policies/`, `plugins/`, `connectors/`, `infrastructure/`, and high-risk skills;
- enable secret scanning and push protection when available;
- prohibit GitHub Actions from receiving write tokens unless a workflow explicitly needs them.

Required status checks (names MAY change; the *categories* MUST exist before `stable` use):

- authorization / isolation tests;
- secret-scan / push-protection equivalent;
- unit and relevant integration tests;
- release-manifest / lockfile integrity when packaging.

CODEOWNERS (spec 9.3) — replace placeholders only after `DECISIONS-NEEDED.md` is answered:

```text
*                         @<GITHUB_ORG>/agent-builders
/policies/legal/          @<LEGAL_OWNER>
/policies/finance/        @<FINANCE_OWNER>
/plugins/                 @<GITHUB_ORG>/agent-platform-admins
/connectors/              @<GITHUB_ORG>/agent-platform-admins
/infrastructure/          @<GITHUB_ORG>/agent-platform-admins
/runbooks/contract-*      @<LEGAL_OWNER>
/runbooks/procure-*       @<FINANCE_OWNER>
```

## 4. The three repositories

### 4.1 `company-agent-distribution`

Shareable Hermes profile distribution (spec 9.1). It MUST NOT contain `.env`, `auth.json`, memories, sessions, browser profiles, exported CRM data, contract files, raw notes, or credentials.

### 4.2 `company-agent-platform`

Service code and deployment configuration, including this file. This working tree is the Phase 0 bootstrap of that repository. `spec/` is locally gitignored and MUST NOT be assumed to be the Git source of truth for implementation history.

### 4.3 `company-knowledge-curated`

Reviewed, shareable company knowledge only. MUST NOT hold raw user dumps or confidential customer/legal documents (spec 9.1). Appropriate content: approved policy text, reusable playbooks, product facts, brand guidance, standard clause guidance, glossary terms, and reviewed research summaries.

## 5. No secrets in Git (spec 9.4, 12.2, 16.3)

Secrets MUST NOT be stored in Git history, distribution files, identity markdown, skills, notes, tool-call arguments when a reference can be resolved, general audit logs, container images, or CI output.

Operators MUST:

- use SSH or the GitHub credential helper;
- never place a personal access token inside a clone URL, script, `.env.EXAMPLE`, or chat message (spec 9.4);
- keep `.env`, `auth.json`, profile state, and raw evidence out of commits (illustrative distribution `.gitignore` in spec 16.3);
- rely on secret scanning and push protection when the org exists;
- treat a leaked secret as an incident: revoke, rotate, and record in the audit store — do not rewrite shared backup history (spec 31.5).

This repository's `.gitignore` currently excludes `spec/`. Additional ignore rules for secrets and user state MUST be added in Phase 1 before any profile or compose secrets exist in the tree.

## 6. Local Git policy for builders (spec 9.4)

```bash
git config --global user.name "<FULL_NAME>"
git config --global user.email "<COMPANY_EMAIL>"
git config --global init.defaultBranch main
git config --global pull.ff only
git config --global fetch.prune true
```

`<FULL_NAME>` and `<COMPANY_EMAIL>` are per-human TODOs. Agent commits on this Pi MAY use the existing host Git identity only for bootstrap commits that contain no secrets.

## 7. Trust-boundary note (spec 5.7)

Git and the release pipeline are a trust boundary against supply-chain drift. Enforcement is protected branches, reviews, checks, dependency locks, and image digest pinning. An agent MAY propose a change from an isolated worktree; CI is the authority that produces stable artifacts (spec 5.4 Class D, 38.14).
