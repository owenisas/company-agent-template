# Runbook: incident kill switch

Spec 29.7. Prefer this over continued chat investigation.

1. Stop all Hermes gateways.
2. Disable shared integration MCP write routes.
3. Revoke company bot and service credentials.
4. Disable external API access at the reverse proxy/VPN.
5. Preserve logs, release manifests, and affected volumes.
6. Identify release, user, profile, connection, and tool calls.
7. Rotate API, database, and approval keys.
8. Restore only a reviewed release.
9. Run authorization and integrity tests before re-enable.

Pi-adapted operator sketch (paths are TODO until compose exists):

```bash
# TODO: confirm unit names and compose project (D015 / D029).
# Do not run these blindly on the live Discord/Cursor host in Phase 1a.
# systemctl --user stop hermes-gateway.service
# sudo docker compose stop  # when a company compose stack exists
```

Break-glass administrator is TODO (D015).
