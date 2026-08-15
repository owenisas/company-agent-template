---
name: incident-triage
description: Triage a security or ops incident and point at the kill switch.
required_environment_variables:
  - COMPANY_KB_TOKEN
---

# Incident Triage

Domain: operations. Spec 19.2 / 19.3. Safe defaults: read-only unless a
named approval skill is used. No credentials in this file.

## Use when

Use at the start of a suspected incident. Prefer containment over investigation theatre.

## Procedure

1. State what is known vs unknown. Do not speculate as fact.
2. If there is unexpected external action, approval bypass, or cross-user exposure, open the kill-switch runbook.
3. Preserve logs and release manifests. Do not wipe evidence.
4. Identify release, user, profile, connection, and tool calls if known.

## Safety

- Do not rotate credentials from chat text. Use the runbook.
- Do not keep the agent running against a compromised profile.
