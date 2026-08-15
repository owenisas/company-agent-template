# User, role, and group registry

**Company slug:** `<company>`
**Normative sources:** spec Sections 2, 4.2, 4.3, 9, 9.2, 11.3, 12.5, 15.3, 15.4, 15.6, 28.3, 29.1, 33.5, 34 Phase 0, 37
**Status:** Phase 0 baseline
**Owner of this registry:** TODO: platform-ops owner
**Review cadence:** MUST be reviewed on every joiner, departure (spec 33.5), and role change

This registry is the authoritative list of people, service principals, platform roles, and GitHub teams for the <Company> Hermes platform. Display names MUST NOT be used as identifiers (spec 11.3). Unknown human names, emails, and GitHub handles MUST remain `TODO:` until recorded in `DECISIONS-NEEDED.md` and then updated here by pull request.

## 1. Normative rules

1. The platform MUST treat identity, authority, and storage as separate questions (spec 4.2).
2. Each employee MUST have one immutable internal slug used in profile names, traces, ACLs, and worktree paths (spec 11.3).
3. `automation` MUST be a non-human service profile. It MUST NOT impersonate an employee or reuse personal OAuth (spec 15.3, 15.4, 15.6).
4. A person MAY belong to several GitHub teams. The company MUST NOT give all three users organization-owner rights. At least two organization owners MUST exist for account recovery; normal work MUST use lower repository roles (spec 9.2).
5. Inheritance in the scope hierarchy (company → team → project/account/matter/campaign → user → task) MUST NOT broaden permissions beyond memberships and the resource owner policy (spec 4.3).
6. On departure, the operator MUST follow spec 33.5: disable identity, revoke personal credentials, remove team memberships, stop the user's Hermes gateway, transfer or preserve data per policy, rotate shared credentials the user could administer, archive the profile, and review recent tool calls.

## 2. Platform roles

These roles apply to Hermes platform authority. They are distinct from GitHub repository permissions (Section 4) and from external connector principals (spec 4.2, 12.1).

| Role | Scope of authority | MAY | MUST NOT | Typical GitHub team |
|---|---|---|---|---|
| `owner` | A named resource (repo, integration, policy domain, secret class, or environment) | Set purpose, classification, membership proposals, and break-glass path for that resource | Act as every other owner by default; hold all three users as org owners | `agent-platform-admins` for platform-wide resources; domain owner otherwise |
| `builder` | Skills, plugins, runbooks, tests, platform code in non-stable channels | Propose changes via `feature/*` or `agent/<user>/<task>` branches and pull requests | Merge policy/plugin/security changes to `main` without required reviews (spec 9.3) | `agent-builders` |
| `approver` | A named action class or restricted domain | Grant time-bound, action-specific approval (spec 12.5) | Approve their own R4 action as the sole control; silently substitute `automation` for a human (spec 15.6) | `legal-approvers`, `finance-approvers`, or named domain approver |
| `viewer` | Stable distribution and approved docs | Install/read stable artifacts and approved knowledge | Change production config, skills, secrets, or ACLs | `agent-users` |

A user MAY hold more than one role. Role assignment for the three employees is TODO until Section 37 user-role decisions are recorded.

## 3. Employee users

Immutable slugs are the identifiers for this template (spec 11.3). Display names, company emails, GitHub handles, platform roles, and GitHub team memberships remain `TODO:` until recorded in `DECISIONS-NEEDED.md`.

| Field | employee-a | employee-b | employee-c |
|---|---|---|---|
| Immutable slug | `employee-a` | `employee-b` | `employee-c` |
| Principal type | Human employee | Human employee | Human employee |
| Display name | <Employee A> | <Employee B> | <Employee C> |
| Company email | TODO: email | TODO: email | TODO: email |
| GitHub account | TODO: handle | TODO: handle | TODO: handle |
| Hermes profile name (target) | `employee-a` | `employee-b` | `employee-c` |
| Current host profile (if any) | TODO: D050 | TODO: D050 | TODO: D050 |
| Platform roles | TODO: owner / builder / approver / viewer | TODO: | TODO: |
| GitHub teams | TODO: | TODO: | TODO: |
| Approval domains | TODO: | TODO: | TODO: |
| Data scope default | Own private profile + authorized company/team/project objects | Same | Same |
| Owner of this identity record | TODO: people/HR owner or platform-ops owner | Same | Same |
| Status | TODO: not production-complete | TODO: not production-complete | TODO: not production-complete |

The named employees (<Employee A>, <Employee B>, <Employee C>) are the candidate pool for all named approver and owner roles (legal, finance, HR, and customer-data approvers; platform-ops; credential owners; restricted-domain and release approvers). Specific role→person assignment MUST remain open (D006, D008–D018) until the principal makes those choices explicitly. Agents MUST NOT invent assignments. Privilege-changing role grants are risk tier R3/R4 (spec 12.5).

D050 (spec 11.3, 15.3, 33.5, 38.1) remains open. Any pre-existing Hermes profiles on the host MUST be listed here only after a human maps them. Do not invent a mapping. Operators MUST NOT retire, merge, or disable legacy profiles until D050 is closed. On a later departure, the operator MUST follow spec 33.5 rather than informal profile reuse.

Each employee profile MUST have a distinct authenticated identity, data directory, user context, API/gateway key, and workspace root before Phase 1 exit (spec 38.1). Cross-user private context MUST be isolated (spec 29.1).

## 4. Service principal

| Field | Value |
|---|---|
| Immutable slug | `automation` |
| Principal type | Non-human Hermes service profile (spec 15.3) |
| Display name | <Company> company automation |
| Hermes profile name | `automation` |
| Owner | TODO: platform-ops owner |
| Scope | `company` — scheduled, background, and event-triggered company work only |
| Credential class allowed | Shared service, and delegated/assumed only after an employee-attributed approval handoff (spec 12.1, 15.6) |
| Break-glass / revoke owner | TODO: named recovery administrator |
| Platform roles | Service executor. MUST NOT be an `approver` for its own consequential actions. |
| GitHub teams | MAY be represented by a machine identity with least privilege. MUST NOT be an organization owner. |
| Status | Planned for Phase 1. MUST NOT be created by copying an employee profile or `.env` (spec 15.5). |

`automation` MUST:

- name a non-human principal, owner, scope, rotation/revocation path, and allowed actions on every connection (spec 15.4);
- record both the triggering human/event and the executing service principal on every trace (spec 15.4, 30.2);
- hand employee-attributed actions to the accountable human; it MUST NOT silently substitute its identity for a human (spec 15.6).

`automation` MUST NOT:

- impersonate an employee or reuse personal OAuth (spec 15.3, 15.4);
- send, publish, sign, pay, delete, deploy, or change privileges without the applicable approval policy (spec 15.3);
- hold unrestricted production-administrator, bank-payment, or signing credentials (spec 15.3);
- execute arbitrary task code on the control-plane host (spec 15.3, 5.2);
- use memory as the system of record for customer, legal, finance, project, or research data (spec 15.4).

### 4.1 Control-plane system principal

| Field | Value |
|---|---|
| Immutable slug | `company-system` |
| Principal type | System / control-plane (not a human, not user-facing automation) |
| Display name | Control-plane system |
| Hermes profile name | none — MUST NOT be a user-facing Hermes profile |
| Owner | TODO: platform-ops owner (D015) |
| Scope | Platform-internal API and service principals only (knowledge-api, approval-api, workers, RLS session context) |
| Credential class allowed | Host/service credentials brokered to those processes. MUST NOT be an employee OAuth or personal token. |
| Break-glass / revoke owner | TODO: named recovery administrator (D015) |
| Platform roles | None of owner / builder / approver / viewer. MUST NOT be granted employee scopes (`user:*/private`, `user:*/restricted`, personal OAuth). |
| GitHub teams | None |
| Status | Seeded as a principal slug in `company-agent-services` for control-plane identity. MUST NOT be used as a Discord/Hermes user. |

`company-system` exists only for platform-internal API/service principals. It MUST NOT run user-facing automation (that is `automation`). It MUST NOT hold employee-only scopes (spec 15.3–15.6).

## 5. GitHub teams (spec 9.2)

These groups MUST exist in the GitHub organization before production repository use. Membership is TODO.

| Team | GitHub permission | Purpose | Owner of the team | Scope | Members |
|---|---|---|---|---|---|
| `agent-platform-admins` | Maintain/Admin | Host, secrets, incident response, releases | TODO: platform-ops owner | Company platform and the three required repos | TODO: named humans; MUST NOT be all three employees as org owners |
| `agent-builders` | Write | Skills, plugins, runbooks, tests, platform code | TODO: engineering owner | `company-agent-distribution`, `company-agent-platform`, and builder-readable curated knowledge | TODO: |
| `agent-users` | Read | Install stable distribution and read approved docs | TODO: platform-ops owner | Stable channel artifacts and `company-knowledge-curated` | All authorized employees SHOULD be members |
| `legal-approvers` | Triage/Read plus approval role | Contract and legal policy review | TODO: legal owner | Restricted legal domain (spec 29.6) | TODO: named legal approver(s) |
| `finance-approvers` | Triage/Read plus approval role | Payments and financial action approval | TODO: finance owner | Restricted finance domain (spec 29.6) | TODO: named finance approver(s) |

Related restricted-domain groups that the spec requires as named approvers, even if they are not GitHub teams in Section 9.2:

| Group | Purpose | Owner | Scope | Members |
|---|---|---|---|---|
| `people-hr-approvers` | HR/people record access, retention, and offboarding exceptions | TODO: people/HR owner | Restricted HR/people domain (spec 29.6) | TODO: |
| `customer-data-approvers` | Bulk customer export, cross-account access, purpose exceptions | TODO: customer-data owner | Restricted customer data (spec 29.6) | TODO: |

Optional repositories after pilot (`company-agent-evals`, `company-agent-connectors`, `company-data-contracts`) MUST reuse these teams rather than inventing unaudited permission sets (spec 9.1).

## 6. Scope and ownership model

Every registry entry MUST have:

- an owner (human or named role pending TODO resolution);
- a scope (`company`, `team/<function>`, `project|account|matter|campaign/<id>`, `user/<slug>`, or `task/<id>`);
- a revocation path (spec 12.2, 33.5).

Default CODEOWNERS mapping (spec 9.3) uses company slug `<company>` only after `TODO: <GITHUB_ORG>` is confirmed. Until then, paths are policy, not live GitHub configuration:

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

## 7. Change control

1. Additions, role changes, and departures MUST be proposed by pull request against this file.
2. Privilege-changing edits are risk tier R3/R4 (spec 12.5) and MUST follow `docs/governance/action-approval-matrix.md`.
3. `automation` MUST NOT be the sole approver of a change to this registry.
4. Unknowns listed as `TODO:` MUST also appear in `DECISIONS-NEEDED-template.md` (forked as `DECISIONS-NEEDED.md`). Closing a TODO here without closing it there is non-conformant.
