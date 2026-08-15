---
name: crm-write-with-approval
description: Prepare a CRM write and apply it only after approval.
required_environment_variables:
  - COMPANY_KB_TOKEN
---

# Crm Write With Approval

Domain: crm-write. Spec 19.2 / 19.3. Safe defaults: read-only unless a
named approval skill is used. No credentials in this file.

## Use when

Use when a CRM field or task must change and a preview can be shown.

## Procedure

1. Identify user, record, connection, and risk tier (R2+).
2. Prepare a preview of the exact mutation.
3. Request approval via the approval service. Do not apply yet.
4. Apply only after a valid, unconsumed approval for that preview hash.
5. Write the result back to the system of record, not memory.

## Safety

- No apply without approval (spec 16.5 rule 7).
- Never substitute automation identity for the human (spec 15.6).
- Autonomous external sends remain disabled at launch.
