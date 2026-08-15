"""Preview then apply (spec 12.2, 12.5, 30.3, ADR-006).

Ordering: tool.preview → approval.request → tool.apply.
A tool.apply without a matching approved preview is rejected.

External writes require preview + approval. The preview holds a stable
action fingerprint and a proposed external-effect description. No secrets.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from packages.approval.models import ApprovalStatus
from packages.approval.service import get_request
from packages.approval.tamper import request_fingerprint, strip_secret_like
from packages.capabilities.registry import POLICY_VERSION, get_capability
from packages.tracing.attribution import attribution_consistent
from packages.tracing.context import RequestContext
from packages.tracing.events import AuditEvent


class Preview(BaseModel):
    preview_id: str
    capability_id: str
    params: dict[str, Any] = Field(default_factory=dict)
    params_fingerprint: str
    effect_description: str
    external_write: bool
    risk_tier: str
    context_principal: str
    created_at: datetime
    connection: str | None = None
    policy_version: str = POLICY_VERSION


class ApplyResult(BaseModel):
    status: str
    approval_id: str | None = None
    preview_id: str | None = None
    attribution: dict[str, str | None] = Field(default_factory=dict)
    event: dict[str, Any] = Field(default_factory=dict)


def _material(capability_id: str, params: dict[str, Any], ctx: RequestContext, connection: str | None, risk_tier: str) -> dict[str, Any]:
    return {
        "capability": capability_id,
        "params": params,
        "principal": ctx.principal_id,
        "connection": connection,
        "policy_version": POLICY_VERSION,
        "risk_tier": risk_tier,
    }


def preview(
    capability: str,
    params: dict[str, Any],
    context: RequestContext,
    *,
    connection: str | None = None,
) -> Preview:
    RequestContext.require(context)
    cap = get_capability(capability)
    if cap is None:
        raise PermissionError("unknown_capability")
    clean = strip_secret_like(params)
    if not isinstance(clean, dict):
        clean = {}
    risk = cap.risk_tier.value
    fingerprint = request_fingerprint(_material(capability, clean, context, connection, risk))
    effect = (
        f"Proposed {capability} as {context.principal_id} "
        f"(risk {risk}, external_write={cap.external_write}). "
        f"Targets={sorted(str(k) for k in clean)}"
    )
    return Preview(
        preview_id=f"prv_{uuid4().hex}",
        capability_id=capability,
        params=clean,
        params_fingerprint=fingerprint,
        effect_description=effect,
        external_write=cap.external_write,
        risk_tier=risk,
        context_principal=context.principal_id,
        created_at=datetime.now(timezone.utc),
        connection=connection,
    )


def apply_requires_approval(preview_obj: Preview, policy: Any | None = None) -> bool:
    _ = policy
    cap = get_capability(preview_obj.capability_id)
    if cap is None:
        return True
    if preview_obj.external_write or cap.external_write:
        return True
    if cap.approval_mode.value not in {None, "none"}:
        return True
    if preview_obj.risk_tier in {"R2", "R3", "R4"}:
        return True
    return False


def apply(
    preview_obj: Preview | None,
    context: RequestContext,
    *,
    capability_id: str,
    params: dict[str, Any],
    approval_id: str | None = None,
    executed_as: str | None = None,
    connection: str | None = None,
) -> ApplyResult:
    RequestContext.require(context)
    if preview_obj is None:
        raise PermissionError("preview required before apply (spec 30.3)")
    cap = get_capability(capability_id)
    if cap is None or preview_obj.capability_id != capability_id:
        raise PermissionError("preview/capability mismatch")

    clean = strip_secret_like(params)
    if not isinstance(clean, dict):
        clean = {}
    conn = connection if connection is not None else preview_obj.connection
    expected = request_fingerprint(
        _material(capability_id, clean, context, conn, preview_obj.risk_tier)
    )
    if expected != preview_obj.params_fingerprint:
        raise PermissionError("fingerprint tamper: params changed after preview")

    needs_approval = apply_requires_approval(preview_obj)
    approval = get_request(approval_id) if approval_id else None
    if needs_approval:
        if approval is None:
            raise PermissionError("approval required before apply")
        if approval.status is not ApprovalStatus.APPROVED:
            raise PermissionError("approval required before apply")
        if approval.params_hash != preview_obj.params_fingerprint:
            raise PermissionError("fingerprint tamper: approval does not match preview")
        if approval.capability != capability_id:
            raise PermissionError("approval/capability mismatch")

    executed = executed_as or context.principal_id
    profile = context.profile_id or context.principal_id
    approval_ref = approval.approval_id if approval else None
    if not attribution_consistent(context.principal_id, profile, executed, conn, approval_ref):
        # Employee-attributed apply with no shared connection is the scaffold default.
        executed = context.principal_id
        if not attribution_consistent(context.principal_id, profile, executed, conn, approval_ref):
            raise PermissionError("attribution_inconsistent")

    event = AuditEvent.from_context(
        context,
        "tool.apply",
        scope=capability_id,
        approval_id=approval_ref,
        executing_principal=executed,
        connection_id=conn,
        requested_by=context.principal_id,
        agent_profile=profile,
        executed_as=executed,
        runbook_id=None,
        worker=None,
    )
    return ApplyResult(
        status="recorded",
        approval_id=approval_ref,
        preview_id=preview_obj.preview_id,
        attribution={
            "requested_by": context.principal_id,
            "agent_profile": profile,
            "executed_as": executed,
            "connection": conn,
            "approval": approval_ref,
        },
        event=event.model_dump(mode="json"),
    )
