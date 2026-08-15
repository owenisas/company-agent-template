# Runbook: approval request

Spec 16.5 rule 7, 12.5, 36.2.

1. Identify requester, action, connection, and credential principal.
2. Build a preview and hash it. Do not apply yet.
3. Call approval_request with the preview hash and expiry.
4. Wait for an approved, unconsumed approval from the required role.
5. Apply exactly the preview. If the payload drifted, request again.
6. Record approval id on the audit trace.
7. Forbidden even with a chat "yes": sign, pay, unrestricted delete, or
   permission grants that policy marks deny (spec 36.1).
