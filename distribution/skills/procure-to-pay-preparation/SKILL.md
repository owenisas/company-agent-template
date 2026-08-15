---
name: procure-to-pay-preparation
description: Prepare a procure-to-pay packet. Does not pay.
required_environment_variables:
  - COMPANY_KB_TOKEN
---

# Procure To Pay Preparation

Domain: finance-read. Spec 19.2 / 19.3. Safe defaults: read-only unless a
named approval skill is used. No credentials in this file.

## Use when

Use to assemble invoice, vendor, and approval context for a human finance owner.

## Procedure

1. Read finance objects that policy marks read-capable (TODO: FINANCE_SYSTEM).
2. Assemble vendor, amount, currency, due date, and supporting docs.
3. Flag missing approvals or classification issues.
4. Stop before any payment, bank-detail change, or transfer.

## Safety

- finance.payment.execute is deny (spec 36.1).
- Not tax, accounting, or professional advice.
- R4 payments require two named finance humans (D012).
