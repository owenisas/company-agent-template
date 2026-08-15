"""audit-consumer process (spec 13.2, 14.3, 30.2, 30.3).

Append-only event sink with full attribution. No off-host export (Phase 5).
"""

from __future__ import annotations

from typing import Any

from packages.tracing.attribution import TraceAttribution
from packages.tracing.context import RequestContext
from packages.tracing.events import AuditEvent

_LOG: list[AuditEvent] = []


def append(event: AuditEvent) -> AuditEvent:
    """Append-only. There is no update/delete API on purpose."""
    _LOG.append(event)
    return event


def append_from_context(
    ctx: RequestContext,
    event_type: str,
    *,
    scope: str | None = None,
    approval_id: str | None = None,
) -> AuditEvent:
    RequestContext.require(ctx)
    event = AuditEvent.from_context(
        ctx, event_type, scope=scope, approval_id=approval_id
    )
    return append(event)


def append_attribution(
    ctx: RequestContext,
    attribution: TraceAttribution,
    event_type: str,
    *,
    scope: str | None = None,
) -> AuditEvent:
    """Record a 30.2/30.3 event with full who/what/connection/approval/runbook/worker."""
    RequestContext.require(ctx)
    event = AuditEvent.from_attribution(
        ctx,
        event_type,
        requested_by=attribution.requested_by,
        agent_profile=attribution.agent_profile,
        executed_as=attribution.executed_as,
        connection=attribution.connection,
        approval=attribution.approval,
        runbook=attribution.runbook,
        worker=attribution.worker,
        triggered_by=attribution.triggered_by,
        scope=scope,
    )
    return append(event)


def list_events() -> list[dict[str, Any]]:
    return [e.model_dump(mode="json") for e in _LOG]


def export_configured() -> bool:
    """Off-host export is Phase 5. Always False in this scaffold."""
    return False


def main() -> None:
    print(
        {
            "service": "audit-consumer",
            "status": "not_configured",
            "export": False,
            "detail": "TODO: durable audit store + off-host backup (D033); no exporter in scaffold",
            "events": len(_LOG),
        }
    )


if __name__ == "__main__":
    main()
