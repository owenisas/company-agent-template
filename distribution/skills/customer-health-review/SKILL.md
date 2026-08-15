---
name: customer-health-review
description: Read-only customer-health and renewal-risk review.
required_environment_variables:
  - COMPANY_KB_TOKEN
---

# Customer Health Review

Domain: customer-success. Spec 19.2 / 19.3. Safe defaults: read-only unless a
named approval skill is used. No credentials in this file.

## Use when

Use to draft an internal health or renewal-risk note from approved systems.

## Procedure

1. Identify the account and the user's access.
2. Read CRM/support/usage only through approved connections.
3. Draft an internal report and suggested tasks. Do not email the customer.
4. Escalate legal/finance items instead of answering them.

## Safety

- Drafts first. No customer-facing send.
- Bulk export of customer data needs a second approver (D014).
