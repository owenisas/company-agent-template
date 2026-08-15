---
name: campaign-preflight
description: Preflight a publishing or outreach campaign. Does not send.
required_environment_variables:
  - COMPANY_KB_TOKEN
---

# Campaign Preflight

Domain: publishing. Spec 19.2 / 19.3. Safe defaults: read-only unless a
named approval skill is used. No credentials in this file.

## Use when

Use before any company send/publish to check audience, copy, suppression, and approval.

## Procedure

1. Identify channel list (TODO: CHANNEL_LIST / D023) and campaign owner.
2. Check suppression, consent, and classification.
3. Produce a preview: audience count, channels, copy hash.
4. Request campaign-owner approval. Do not send.

## Safety

- Autonomous external sends are disabled at launch (ADR-0001).
- No send, publish, or permission change from this skill.
