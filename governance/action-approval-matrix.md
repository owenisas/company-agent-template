# Action and approval matrix

**Company slug:** `<company>`
**Normative sources:** spec Sections 2, 4.2, 8, 12.4, 12.5, 15.3, 15.4, 15.6, 28.3, 29.6, 33.5, 34 Phase 0, 38.13, 38.17
**Status:** Phase 0 baseline
**Owner of this matrix:** TODO: platform-ops owner
**Review cadence:** Before enabling any write connector, and after every privilege or domain-owner change

Approvals MUST be time-bound, action-specific, and invalidated when material parameters change (spec 12.5). Enforcement MUST live outside the model (MCP/API/approval service), not in prompt text (spec 29.3, 38.13).

## 1. Identity substitution constraint (spec 15.4 / 15.6)

The following rules are invariant and override every cell below:

1. `automation` MUST NOT impersonate an employee.
2. `automation` MUST NOT reuse an employee's personal OAuth token.
3. A scheduled workflow that needs an employee-attributed action MUST follow a handoff: automation prepares the exact payload, requests approval from the accountable employee, and the final connector uses the approved delegated or company principal according to policy.
4. Automation MUST NEVER silently substitute its identity for a human.
5. Traces MUST record requester (human or schedule), profile, executing principal, connection, and approval id (spec 30.2).
6. High-risk credentials MUST be brokered; Hermes MUST NOT receive the raw secret (spec 12.4).

## 2. Risk tiers (spec 12.5)

| Tier | Meaning | Default policy |
|---|---|---|
| R0 | Read | Automatic within ACL |
| R1 | Reversible internal | Automatic or user-configurable |
| R2 | External / reputational | Explicit user or business-owner approval |
| R3 | Contractual / financial / production | Named approver and evidence checks |
| R4 | Irreversible / high impact | Two-person control **or** direct authorized human execution |

Autonomous external sends are **disabled at launch** (spec 8). Personal memory writes and skill self-modification require approval during the pilot (spec 8).

## 3. Matrix

Named approver humans are `TODO:` (spec 37). Until they are bound, the **role** is mandatory and the **action is blocked in production**. Restricted-domain rows satisfy the Phase 0 requirement that those domains have named approver *roles*; human names remain a documented gap.

| Action class | Risk tier | Required approval | Approving role | Named human (Phase 0) | Automation (`automation`) | Notes |
|---|---|---|---|---|---|---|
| Signing (contracts, waivers, filings) | R4 | Two-person **or** direct authorized human execution | `legal-approvers` plus the authorized signer role | TODO: legal owner / named signer | MUST NOT sign. MAY prepare a draft and request approval. | Spec 29.6 legal: general agent cannot sign or waive rights. Credential brokered. |
| Payment (send funds, change bank details) | R4 | Two-person control | `finance-approvers` (two distinct humans) | TODO: finance owner and second finance approver | MUST NOT pay. MAY prepare a payment draft id. | Spec 12.4, 29.6. Exact amount/vendor/account in the approval. Duplicate-invoice and change-of-bank checks required. |
| Destructive production (delete prod data, drop schemas, destroy volumes, terminate customer accounts) | R4 | Two-person control | `agent-platform-admins` **and** the data-domain approver (legal / finance / customer-data / people-hr as applicable) | TODO: platform-ops owner + domain owner | MUST NOT execute unless a pre-approved runbook grant names the exact object. MUST NOT self-approve. | Legal hold overrides deletion (spec 31.5). |
| Privilege change (roles, GitHub teams, org owners, ACL broaden, secret-scope expand, offboarding exceptions) | R3 default; R4 when granting org-owner, production-admin, payment, or signing | Named approver; two-person when the change is R4 | `agent-platform-admins` for platform privilege; domain approver when a restricted ACL is widened | TODO: platform-ops owner; TODO: people/HR owner for joiner/leaver | MUST NOT change privileges. MAY open a registry PR or approval request. | Spec 33.5 departure is a human-operated runbook. All three employees MUST NOT be org owners (spec 9.2). |
| External send (email, Discord non-allowlisted destinations, customer messages, CRM outbound sequences) | R2; R3 if contractual or customer-official | Explicit user or business-owner approval. Autonomous sends disabled at launch. | Accountable employee for personal-attributed mail; TODO: communications / revenue owner for company senders | TODO: communications owner | MUST prepare payload and request approval. MUST NOT send under a human identity. MUST NOT send autonomously at launch (spec 8). | Spec 15.6 handoff required for employee-attributed sends. |
| Publish (web, social, email campaign, public company claim) | R2; R3 if the claim is contractual or a public company statement | Explicit campaign/business-owner approval; public claims also need applicable review (spec 28.3) | TODO: marketing / publishing owner; legal-approvers when the copy makes a legal claim | TODO: marketing owner | MAY create drafts and previews only. | Channel list is TODO: `<CHANNEL_LIST>`. |
| Deploy (promote `testing` → `stable`, production compose/systemd change, pin digest change) | R3 | Named approver and evidence checks; two reviewers for stable policy/plugin/security changes (spec 8, 9.3) | `agent-platform-admins` plus required CODEOWNERS | TODO: two stable-release approvers (`<PERSON_1>`, `<PERSON_2>` in spec 5.8) | MAY run checks and open the release PR. MUST NOT push `main` or apply production without approval. | Rollback and kill switch remain human-operable (spec 29.7, 38.15). |
| Memory write (personal `MEMORY.md` / profile memory; automation operational checkpoints) | R1 for user-approved personal notes after pilot; **approval required during pilot** (spec 8). Automation memory is R1 only for operational checkpoints (spec 15.4). | Named user (self) during pilot for personal memory; platform owner if automation memory stores business records (forbidden — treat as R3 violation) | The user for their profile; `agent-platform-admins` if a service profile is in doubt | Each `company-user-*` for their memory | MAY write small operational state (checkpoints, source ids, failure patterns). MUST NOT store customer, legal, finance, project, or research records in memory. | Memory is not a system of record (spec 15.4). |
| Skill change (company skills, overlays, specialists, `SOUL.md` / `AGENTS.md` / distribution config) | R2 for low-risk skill text; R3 for plugins, policies, connectors, high-risk skills | Approval required. Company skills changed only by PR (spec 8). One reviewer MAY suffice for low-risk skill text; two reviewers MUST review policy/plugin/security into `main` (spec 9.3). | `agent-builders` review + CODEOWNERS; `agent-platform-admins` for plugins/connectors | TODO: builders and admins | MUST NOT self-modify company skills on stable. MAY open `agent/automation/<task>` PRs. | Skill self-modification by a live agent against stable is forbidden. |

## 4. Restricted-domain approvers (spec 29.6, 34 Phase 0)

These are the named approver **bindings** required before production data in that domain is connected.

| Restricted domain | Approver role / group | Named human | Second human (when R4 / two-person) | May automation act? |
|---|---|---|---|---|
| Legal | `legal-approvers` | TODO: legal owner / counsel | TODO: second legal or executive approver for sign/waive | Prepare only |
| Finance | `finance-approvers` | TODO: finance owner | TODO: second finance approver | Prepare only |
| HR / people | `people-hr-approvers` | TODO: people/HR owner | TODO: second people or legal approver for bulk export or offboarding exceptions | Prepare only |
| Customer data | `customer-data-approvers` | TODO: customer-data owner | TODO: second approver for bulk export | Read within ACL; bulk export needs approval |

Until each TODO human is recorded in `docs/governance/user-role-group-registry.md` and `DECISIONS-NEEDED.md` is updated, production connectors for that domain MUST remain disconnected.

## 5. Channel defaults at launch (spec 5.8, 8)

| Channel | External write | Approval posture |
|---|---|---|
| `working` | Disabled; sandbox tenants only | Builders only |
| `testing` | Staging/test accounts only | Opt-in users |
| `stable` | Only through approved connections and gates | This matrix |

## 6. Change control

Edits to this matrix are themselves a privilege change (R3) and MUST be merged to `main` with two reviewers when they weaken a control. `automation` MUST NOT be the sole approver of a matrix change.
