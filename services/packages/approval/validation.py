"""Pure approval predicates (spec 12.4, 12.5, 15.6).

can_request / can_approve honor:
  - named approvers when the request lists them
  - R4 two-person control
  - automation MUST NOT self-approve (action-approval-matrix §1)

Named humans remain TODO (D011–D018). Until then the scaffold accepts
known employee slugs when listed on the request.
"""

from __future__ import annotations

from datetime import datetime, timezone

from packages.approval.models import ApprovalRequest, ApprovalStatus
from packages.authz.principals import Principal, PrincipalType
from packages.authz.scopes import RiskTier
from packages.capabilities.registry import capability_policy, get_capability


def _tier(value: str | RiskTier) -> RiskTier:
    if isinstance(value, RiskTier):
        return value
    text = str(value).upper()
    return RiskTier(text if text.startswith("R") else f"R{text}")


def can_request(principal: Principal, capability_id: str, memberships: list[str]) -> bool:
    """Whether this principal may open an approval request."""
    if not principal.active:
        return False
    if principal.principal_type is PrincipalType.SERVICE:
        return False
    decision = capability_policy(capability_id)
    if decision.effect == "deny" and decision.reason == "unknown_capability":
        return False
    cap = get_capability(capability_id)
    if cap is None:
        return False
    if cap.groups and frozenset(memberships).isdisjoint(cap.groups):
        return False
    return True


def can_approve(approver: Principal, request: ApprovalRequest, *, now: datetime | None = None) -> bool:
    """Whether this principal may cast an approval on the request."""
    now = now or datetime.now(timezone.utc)
    if request.status not in {ApprovalStatus.PENDING}:
        return False
    if request.expires_at <= now:
        return False
    if not approver.active or approver.principal_type is not PrincipalType.EMPLOYEE:
        return False
    if approver.slug == request.requester:
        return False
    if request.approvers and approver.slug not in request.approvers:
        return False
    return True
