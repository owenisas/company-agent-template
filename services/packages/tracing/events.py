"""Append-only audit event schema (spec 4.1 Trace, 14.3 audit_events, 30.2, 30.3).

who / what / connection / approval / runbook / worker.
Export destination is not configured (Phase 5).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from packages.tracing.context import RequestContext


class AuditEvent(BaseModel):
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    trace_id: str
    request_id: str
    event_type: str
    requesting_principal_id: str
    executing_principal: str | None = None
    profile_id: str | None = None
    release_id: str
    scope: str | None = None
    approval_id: str | None = None
    skill_id: str | None = None
    plugin_id: str | None = None
    tool_id: str | None = None
    connection_id: str | None = None
    result: str = "recorded"
    details_redacted: dict[str, Any] = Field(default_factory=dict)
    # Spec 30.2 full attribution (aliases kept so existing callers still work).
    requested_by: str | None = None
    agent_profile: str | None = None
    executed_as: str | None = None
    runbook_id: str | None = None
    worker: str | None = None
    triggered_by: str | None = None

    @classmethod
    def from_context(
        cls,
        ctx: RequestContext,
        event_type: str,
        *,
        scope: str | None = None,
        approval_id: str | None = None,
        **kwargs: Any,
    ) -> "AuditEvent":
        requested_by = kwargs.pop("requested_by", ctx.principal_id)
        agent_profile = kwargs.pop("agent_profile", ctx.profile_id)
        executed_as = kwargs.pop("executed_as", kwargs.get("executing_principal"))
        return cls(
            trace_id=ctx.trace_id,
            request_id=ctx.request_id,
            event_type=event_type,
            requesting_principal_id=ctx.principal_id,
            profile_id=ctx.profile_id,
            release_id=ctx.release_id,
            scope=scope,
            approval_id=approval_id,
            requested_by=requested_by,
            agent_profile=agent_profile,
            executed_as=executed_as,
            **kwargs,
        )

    @classmethod
    def from_attribution(
        cls,
        ctx: RequestContext,
        event_type: str,
        *,
        requested_by: str,
        agent_profile: str,
        executed_as: str,
        connection: str | None = None,
        approval: str | None = None,
        runbook: str | None = None,
        worker: str | None = None,
        triggered_by: str | None = None,
        scope: str | None = None,
    ) -> "AuditEvent":
        return cls.from_context(
            ctx,
            event_type,
            scope=scope,
            approval_id=approval,
            executing_principal=executed_as,
            connection_id=connection,
            requested_by=requested_by,
            agent_profile=agent_profile,
            executed_as=executed_as,
            runbook_id=runbook,
            worker=worker,
            triggered_by=triggered_by,
        )
