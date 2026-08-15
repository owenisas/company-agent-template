---
name: audit-trace-explanation
description: Explain a redacted audit trace to an authorized reviewer.
required_environment_variables:
  - COMPANY_KB_TOKEN
---

# Audit Trace Explanation

Domain: operations. Spec 19.2 / 19.3. Safe defaults: read-only unless a
named approval skill is used. No credentials in this file.

## Use when

Use when a human asks what an agent run did, as whom, and under which approval.

## Procedure

1. Load the trace by id. Distinguish requester, profile, and executed-as principal.
2. List tools, skills, connections, and approval ids.
3. Redact secrets and unauthorized records.
4. Do not reconstruct raw prompts that policy says to drop.

## Safety

- Never present a bot action as if the employee did it (spec 30.2).
- Do not dump another user's private memory.
