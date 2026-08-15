# Runbook: contract

Phase 4 §4490. Skill `contract-first-pass-review`.
Specialists: `legal.document-review`, `legal.compliance-checker`.
Normative: `governance/action-approval-matrix.md` §3 Signing,
`policies/capabilities.yaml` `legal.contract.sign` (deny).

## When to use

First-pass review of a contract or redline draft. Not execution, not
legal advice to a counterparty, not privilege waiver.

## Inputs

- Requester (founder / legal team only)
- Matter id and jurisdiction (required by overlay)
- Document locator (TODO: repository — **D021**)
- Question (risk scan vs draft redline)

## Steps

1. Confirm the requester is in `legal` / founder. Otherwise refuse.
2. Load only a contract specialist. Matter-scoped context; no personal
   memory (overlay).
3. Read the contract via `contract_get` / `kb_get_document`. Do not
   embed restricted legal text into general company search.
4. Produce a first-pass finding with citations, jurisdiction, and an
   uncertainty statement (spec 18.7 requirements).
5. Internal draft redline: automatic. Sending a redline to a
   counterparty: `legal_approval_required` →
   `runbooks/approval-request.md`.
6. Signing is **forbidden**. `legal.contract.sign` has `effect: deny`.
   Even a chat "yes" is not approval (matrix R4).
7. Trace: matter id, specialist, overlay version, approval id.

## Approval gates

| Action | Tier | Gate |
|---|---|---|
| First-pass review | R1 | Automatic |
| Create internal draft/redline | R1 | Automatic |
| Send redline externally | R3 | `legal-approvers` — TODO **D011** |
| Sign / waive rights | R4 | Forbidden for agents. Human signer TODO **D018** |

**D021** (contract repository) is open: no production legal connector.

## Outputs

- Review findings with clause locators
- Optional internal redline draft
- Explicit "not signed / not legal advice" statement

## What must NEVER happen

- Sign, waive, or file
- Send a redline without legal approval
- Cross-matter retrieval
- Put privileged text in general telemetry or personal MEMORY.md
- Pay or change bank details as a side effect of review
