# Runbook: procure-to-pay

Phase 4 §4490. Skill `procure-to-pay-preparation`.
Specialists: `finance.accounts-payable`, `finance.fpa-analyst`,
`finance.bookkeeper`.
Normative: matrix §3 Payment (R4),
`policies/capabilities.yaml` `finance.payment.execute` (deny).

## When to use

Prepare an invoice package, flag duplicates, or draft a payment
request. Never execute payment or change bank details.

## Inputs

- Requester (finance owner / ops)
- Vendor, invoice, amount, currency, due date
- Bank / account identifiers **only as already stored references**
  (TODO: finance system — **D022**)
- Duplicate-invoice and change-of-bank check results

## Steps

1. Confirm finance ACL. Restricted domain. No general-search embed.
2. Load an AP/FP&A specialist. Tools: `invoice_get`, `vendor_get`,
   `kb_search`. `payment_create` is denylisted.
3. Assemble a payment **draft**: vendor, amount, account reference,
   invoice hash, duplicate check, change-of-bank check.
4. `finance.payment.execute` is `effect: deny`. Do not call a payment
   API even if a human types "just pay it".
5. If a human payment is intended: create an approval request for
   **two** `finance-approvers` (TODO **D012**) with the exact
   amount/vendor/account. Agent stops after the draft.
6. Bank-detail change is R4 two-person and agent-forbidden.
7. Trace draft id, checks, specialist. No raw account numbers in
   general logs.

## Approval gates

| Action | Tier | Gate |
|---|---|---|
| Prepare invoice / payment draft | R1 | Automatic for finance group |
| Execute payment | R4 | Forbidden for agents. Two humans D012 |
| Change bank details | R4 | Forbidden for agents |
| Sign related contract | R4 | Forbidden; signer D018 |

**D022** open: no production finance connector.

## Outputs

- Payment draft id + checklist (duplicate, bank-change, amount)
- Approval request for humans (optional)
- Explicit "not paid" status

## What must NEVER happen

- Send funds
- Change vendor bank details
- Reuse a payment credential inside Hermes context
- One-person approve-and-pay
- Store full PAN / account numbers in MEMORY.md or traces
