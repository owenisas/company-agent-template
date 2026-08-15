# Runbook: lead-to-cash

Phase 4 §4490. Skills `crm-read-analysis`, `crm-write-with-approval`.
Specialists: `revenue.*`, `crm.architect`.
Normative: `governance/action-approval-matrix.md`,
`distribution/policies/capabilities.yaml`.

## When to use

Pipeline analysis, discovery prep, opportunity hygiene, or a proposed
CRM field update on an in-scope account. Not for signing, invoicing,
or outbound send.

## Inputs

- Requester identity and role (`revenue`, `executive`, or deny)
- Account / opportunity ids (TODO: object/field list — **D020**)
- Decision asked (read vs proposed write)
- Connection: `company/crm-readonly` for reads; write connections stay
  disconnected until D020/D021 close

## Steps

1. Identify requester, record scope, and risk tier (R0 read / R3 write).
2. Load only a lead-to-cash specialist from `specialists/manifest.yaml`.
   Do not load legal/finance specialists for a pipeline question.
3. Search company knowledge, then CRM read tools
   (`crm.account.read` — approval none, groups revenue/CS/executive).
4. If the answer is analysis only: write an internal memo. Stop.
5. If a CRM field would change: build a preview (old/new) and hash it.
   Call `runbooks/approval-request.md`. Gate:
   `crm.opportunity.update` → `approval: record-owner`, `preview: required`.
6. Apply **exactly** the approved preview. Drift → new request.
7. Record specialist id, overlay version, connection, and approval id
   on the audit trace (spec 30.1).

## Approval gates

| Action | Tier | Gate |
|---|---|---|
| Account/opportunity read | R0 | Automatic within ACL |
| Opportunity field update | R3 | Record-owner preview/apply |
| External sequence send | R2 | Campaign/business owner; autonomous send **disabled** (spec 8) |
| Bulk CRM export | R3 | `customer-data-approvers` — TODO human **D014** |

Named approvers are TODO (**D011–D018**). Until bound, production CRM
writes stay blocked.

## Outputs

- Pipeline or discovery memo with source ids
- Optional approval request id + preview hash
- Audit trace (requester, specialist, connection, approval)

## What must NEVER happen

- Send outbound mail/Discord/CRM sequences without approval
- Write CRM without preview/apply
- Use an employee personal OAuth token as `company-automation`
- Impersonate the account owner
- Load out-of-scope objects while **D020** is open
- Treat the specialist prompt as a write grant
