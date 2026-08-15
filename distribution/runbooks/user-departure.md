# Runbook: user departure

Spec 33.5.

1. Disable company identity/VPN.
2. Revoke personal OAuth and API keys.
3. Remove user from GitHub teams and capability groups.
4. Stop the user's Hermes gateway.
5. Transfer business-owned notes/objects under policy; preserve private data appropriately.
6. Revoke or rotate any shared credential the user could access administratively.
7. Archive profile with restricted access and retention date.
8. Review recent tool calls and exports.
9. Confirm no task worktrees or deploy keys remain active.

Named people/HR owner is TODO (D013). Do not invent a human owner.
