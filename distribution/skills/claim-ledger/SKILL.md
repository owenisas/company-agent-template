---
name: claim-ledger
description: Maintain a claim ledger with support, contradiction, and uncertainty.
required_environment_variables:
  - COMPANY_KB_TOKEN
---

# Claim Ledger

Domain: research. Spec 19.2 / 19.3. Safe defaults: read-only unless a
named approval skill is used. No credentials in this file.

## Use when

Use when a decision needs a durable list of claims rather than a narrative summary.

## Procedure

1. Normalize each claim as a single testable statement.
2. Attach source ids, dates, and confidence.
3. Record contradictions instead of averaging them away.
4. Mark unknowns explicitly.
5. Do not write the ledger into CRM, contracts, or finance systems.

## Safety

- Ledger writes are internal evidence only.
- Promoting a claim to company truth requires knowledge-owner approval.
