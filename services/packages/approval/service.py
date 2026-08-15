"""In-memory approval flow (spec 12.4). Credential-free scaffold.

Flow: create → validate → time-bound/action-specific → resolve → immutable outcome.

TODO: D049 approval UX / notification service key.
TODO: D011–D018 named approver humans.
TODO: credential broker MUST NOT live here (spec 12.4).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from packages.approval.models import ApprovalRequest, ApprovalStatus
from packages.approval.tamper import request_fingerprint
from packages.approval.validation import can_approve, can_request
from packages.authz.principals import parse_principal
from packages.authz.scopes import RiskTier
from packages.capabilities.registry import POLICY_VERSION, capability_policy, get_capability
from packages.tracing.context import RequestContext

DEFAULT_TTL = timedelta(hours=4)  # scaffold default; production TTL is D061

_STORE: dict[str, ApprovalRequest] = {}


def reset_store() -> None:
    _STORE.clear()


def get_request(approval_id: str) -> ApprovalRequest | None:
    return _STORE.get(approval_id)


def _material(
    *,
    capability: str,
    params: dict[str, Any],
    principal: str,
    connection: str | None,
    policy_version: str,
    risk_tier: str,
) -> dict[str, Any]:
    return {
        "capability": capability,
        "params": params,
        "principal": principal,
        "connection": connection,
        "policy_version": policy_version,
        "risk_tier": risk_tier,
    }


def create_request(
    ctx: RequestContext,
    capability_id: str,
    params: dict[str, Any] | None = None,
    *,
    named_approvers: tuple[str, ...] | list[str] = (),
    allow_denied_capability: bool = False,
    now: datetime | None = None,
    ttl: timedelta | None = None,
    policy_version: str | None = None,
    preview_hash: str | None = None,
    connection: str | None = None,
) -> ApprovalRequest:
    RequestContext.require(ctx)
    now = now or datetime.now(timezone.utc)
    params = dict(params or {})
    version = policy_version or POLICY_VERSION
    if version != POLICY_VERSION:
        raise ValueError("policy_version mismatch")

    principal = parse_principal(ctx.principal_id)
    decision = capability_policy(capability_id)
    cap = get_capability(capability_id)
    if cap is None:
        raise PermissionError("unknown_capability")
    if decision.effect == "deny" and decision.reason == "unknown_capability":
        raise PermissionError("unknown_capability")
    if decision.effect == "deny" and not allow_denied_capability:
        raise PermissionError("capability_denied")
    if not allow_denied_capability and not can_request(principal, capability_id, ctx.memberships):
        raise PermissionError("automation_never_requests_consequential")

    risk = cap.risk_tier
    two_person = risk is RiskTier.R4 or cap.approval_mode.value == "two-person"
    material = _material(
        capability=capability_id,
        params=params,
        principal=ctx.principal_id,
        connection=connection,
        policy_version=version,
        risk_tier=risk.value,
    )
    params_hash = request_fingerprint(material)
    if preview_hash and preview_hash != params_hash:
        raise ValueError("preview_hash does not match material params")

    for existing in _STORE.values():
        if (
            existing.requester == ctx.principal_id
            and existing.capability == capability_id
            and existing.params_hash == params_hash
            and existing.status is ApprovalStatus.PENDING
            and existing.expires_at > now
        ):
            raise ValueError("duplicate pending approval request")

    req = ApprovalRequest(
        requester=ctx.principal_id,
        principal=ctx.principal_id,
        profile=ctx.profile_id,
        capability=capability_id,
        params_hash=params_hash,
        risk_tier=risk.value,
        approvers=tuple(named_approvers),
        created_at=now,
        expires_at=now + (ttl or DEFAULT_TTL),
        requires_two_person=two_person,
        policy_version=version,
        connection=connection,
        preview_hash=preview_hash or params_hash,
        reason=decision.reason,
    )
    _STORE[req.approval_id] = req
    return req


def resolve(
    approval_id: str,
    actor: str,
    decision: str,
    *,
    now: datetime | None = None,
) -> ApprovalRequest:
    now = now or datetime.now(timezone.utc)
    req = _STORE[approval_id]
    if req.status in {ApprovalStatus.APPROVED, ApprovalStatus.DENIED, ApprovalStatus.CONSUMED}:
        raise PermissionError("immutable outcome")
    if req.expires_at <= now:
        req.status = ApprovalStatus.EXPIRED
        raise PermissionError("expired")
    if req.status is ApprovalStatus.EXPIRED:
        raise PermissionError("expired")

    wanted = decision.lower()
    approver = parse_principal(actor)
    if wanted == "approved":
        if not can_approve(approver, req, now=now):
            raise PermissionError("cannot_approve")
        if actor not in req.approved_by:
            req.approved_by.append(actor)
        if req.requires_two_person and len(set(req.approved_by)) < 2:
            req.status = ApprovalStatus.PENDING
            return req
        req.status = ApprovalStatus.APPROVED
        req.outcome_recorded = True
        return req
    if wanted == "denied":
        if not can_approve(approver, req, now=now):
            raise PermissionError("cannot_approve")
        req.status = ApprovalStatus.DENIED
        req.outcome_recorded = True
        return req
    raise ValueError(f"unknown decision: {decision}")
