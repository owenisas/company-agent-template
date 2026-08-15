# Phase 0 exit check

**Company slug:** `<company>`
**Normative sources:** spec Sections 2, 12.2, 29.6, 34 Phase 0, 37, 38
**Date:** 2026-08-14
**Scope:** Governance and inventory only. This check does **not** authorize production installation.

Spec 34 Phase 0 deliverables and exit criteria are evaluated below. Verdicts:

- **PASS** — the criterion is met with cited artifacts.
- **FAIL** — a required artifact or control is missing.
- **GAP** — the artifact exists, but a human input listed in `DECISIONS-NEEDED.md` is still required before the criterion can be treated as production-true.

## 1. Deliverable completeness

| Deliverable (spec 34 Phase 0) | File | Verdict |
|---|---|---|
| User / role / group registry | `docs/governance/user-role-group-registry.md` | PASS (placeholders + TODOs as required) |
| Data classification and retention policy | `docs/governance/data-classification-retention.md` | PASS (policy exists; domain periods TODO) |
| Integration inventory and owners | `docs/governance/integration-inventory.md` | PASS (every required integration listed) |
| Action / approval matrix | `docs/governance/action-approval-matrix.md` | PASS (action classes and roles listed) |
| GitHub organization controls | `docs/governance/github-org-controls.md` | PASS (policy; org name TODO) |
| Architecture decision record | `docs/adr/0001-initial-platform-decisions.md` | PASS (Section 8 + 25–34; Status Accepted) |
| Consolidated human decisions | `DECISIONS-NEEDED.md` | PASS (D001–D051 open) |

## 2. Exit criteria

### 2.1 Every shared credential has an owner and purpose

**Spec:** 12.2, 12.3, 29.5, 34 Phase 0

**Covered in:** `docs/governance/integration-inventory.md` Sections 2–4

**What is true:** Every required integration row has a purpose and an owner *field*. Shared credentials are forbidden from being issued while that owner is `TODO:`. Any present-ungoverned credentials on the host are inventoried as risk, not authorized.

**What is not true:** Named human owners are still open (at least D015, D028, D051, plus system owners on CRM/contracts/finance/publishing).

**Verdict:** **GAP**

**Input needed:** Close D015, D020–D024, D028, D034, D048, D051 (named owner + purpose + credential class for each shared credential that will exist in Phase 1). Until then, issue **zero** new production shared credentials.

### 2.2 Restricted domains have named approvers

**Spec:** 29.6, 12.5, 34 Phase 0

**Covered in:** `docs/governance/action-approval-matrix.md` Sections 3–4; groups in `docs/governance/user-role-group-registry.md` Section 5

**What is true:** Legal, finance, HR/people, and customer data have approver *roles* (`legal-approvers`, `finance-approvers`, `people-hr-approvers`, `customer-data-approvers`). R4 signing and payment require two-person or direct human execution. Automation MUST NOT substitute identity (spec 15.6).

**What is not true:** Spec 34 asks for **named** approvers. Human names are `TODO:` (D011–D014, D017, D018).

**Verdict:** **GAP**

**Input needed:** Bind D011–D014 and D017–D018 to real humans (two finance humans for R4). Production legal/finance/HR/customer connectors MUST stay disconnected until those names exist in the registry.

### 2.3 No production installation begins with unknown data scope

**Spec:** 34 Phase 0, 37, 28.1, 31.5

**Covered in:** `docs/governance/data-classification-retention.md` Sections 1, 2, 6; `DECISIONS-NEEDED.md` source-system block

**What is true:** Classification levels are defined. Unknown scopes are enumerated, not guessed. The policy states that a connector whose class, owner, objects, and retention cannot be stated MUST stay disconnected. Working-channel synthetic/redacted use remains allowed (spec 5.8).

**What is not true:** CRM, contract repository, finance system, publishing channels, residency, and whether Notion/Discord/outreach stores are in scope are unknown (D020–D027, D030, D036). A production install that connected those systems *now* would begin with unknown data scope.

**Verdict:** **GAP** (control is documented; production data scope is still unknown)

**Input needed:** Close D020–D027, D030, D036, or record an explicit “out of scope for Phase 1” for each. Phase 1 runtime bootstrap on synthetic data MAY proceed; production source connections MUST NOT.

## 3. Overall Phase 0 verdict

| Layer | Verdict |
|---|---|
| Required documents written | **PASS** |
| Spec 34 exit criteria as production-true statements | **GAP** |
| Authorization to start production installation | **FAIL** — must not start |
| Authorization to start Phase 1 *runtime* on synthetic/redacted data after these docs | Not blocked by Phase 0 artifacts; still blocked for any production connector |

**Phase 0 exit-check verdict: GAP**

Governance and inventory exist and use normative MUST/SHOULD/MAY language. The three exit criteria are not production-closed because owners, named restricted-domain approvers, and source-system data scope remain human TODOs in `DECISIONS-NEEDED.md` (D001–D051). That is an expected Phase 0 outcome: the gaps are explicit, so production installation cannot begin under unknown scope.

## 4. Next action

Humans answer `DECISIONS-NEEDED.md`. A follow-up change patches the cited files and re-runs this checklist. Re-open this file and flip a criterion to PASS only when the cited D-items are Done.
