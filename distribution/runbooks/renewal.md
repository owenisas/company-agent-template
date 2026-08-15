# Runbook: renewal

Phase 4 §4490. Skill `customer-health-review`.
Specialists: `customer.success-manager`, `customer.account-planner`.
Cron sketch: `cron/renewal-risk.yaml` (disabled).
Normative: matrix customer-data + external send rows,
`crm.account.read`.

## When to use

Renewal risk review, health scoring, or an account plan. Not
renegotiating or signing a contract, not collecting payment.

## Inputs

- Requester (customer-success / revenue / executive)
- Account and renewal ids (TODO: CRM objects — **D020**)
- Horizon (e.g. 90-day renewals)
- Whether a customer-facing message is requested

## Steps

1. Confirm ACL. Customer records are `confidential` / `restricted`
   (classification policy). No bulk dump.
2. Load a renewal specialist. Read `crm.account.read` and
   `crm_renewal_read` only.
3. Produce an internal health review: usage/signals, risks, next
   action, citations.
4. Customer-facing note: preview + record-owner approval
   (`runbooks/approval-request.md`). Automation MUST NOT send as the
   CSM.
5. Commercial change (term, price, concession): treat as contract /
   lead-to-cash, not this runbook. Hand off.
6. Bulk export of customer lists: `customer-data-approvers`
   (TODO **D014**).
7. Trace account id, specialist, approval.

## Approval gates

| Action | Tier | Gate |
|---|---|---|
| Internal health review | R0/R1 | Automatic within ACL |
| Customer message | R2 | Record owner / CSM |
| Commercial concession | R3 | Revenue + legal as applicable (D011/D018) |
| Bulk customer export | R3 | D014 second approver |

## Outputs

- Health review / account plan
- Optional customer-message preview + approval id

## What must NEVER happen

- Sign a renewal or waive terms
- Execute or request payment
- Cross-account retrieval or unapproved bulk export
- Write health notes into another user's personal memory
- Connect production CRM while **D020** is open
