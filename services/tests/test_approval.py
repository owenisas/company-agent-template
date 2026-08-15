"""Approval fingerprint, two-person R4, expiry (spec 12.4, 12.5, 36.2)."""

from datetime import datetime, timedelta, timezone

import pytest

from packages.approval.models import ApprovalStatus
from packages.approval.service import create_request, reset_store, resolve
from packages.approval.tamper import fingerprints_match, request_fingerprint
from packages.approval.validation import can_approve, can_request
from packages.authz.principals import employee, service
from packages.authz.scopes import Scope
from packages.tracing.context import RequestContext


def _ctx(principal: str, memberships: list[str] | None = None) -> RequestContext:
    return RequestContext(
        trace_id="trc_approval",
        request_id="req_approval",
        principal_id=principal,
        profile_id=principal,
        memberships=memberships or ["all-employees", "revenue", "engineering"],
        release_id="scaffold",
        purpose="phase3-test",
    )


def setup_function() -> None:
    reset_store()


def test_fingerprint_changes_when_material_params_change():
    base = {
        "capability": Scope.CRM_OPPORTUNITY_UPDATE,
        "params": {"opportunity_id": "opp_1", "stage": "closed-won"},
        "principal": "employee-a",
        "connection": "company/crm-readonly",
        "policy_version": "1.0.0",
        "risk_tier": "R3",
    }
    original = request_fingerprint(base)
    tampered = dict(base)
    tampered["params"] = {"opportunity_id": "opp_1", "stage": "closed-lost"}
    changed = request_fingerprint(tampered)
    assert original.startswith("sha256:")
    assert original != changed
    assert fingerprints_match(original, changed) is False


def test_r4_requires_two_distinct_employee_approvers():
    requester = employee("employee-a")
    first = employee("employee-b")
    second = employee("employee-c")
    bot = service()
    ctx = _ctx("employee-a", ["all-employees", "finance-approvers"])
    req = create_request(
        ctx,
        capability_id=Scope.FINANCE_PAYMENT,
        params={"payment_draft_id": "pay_1", "amount": "100.00"},
        named_approvers=("employee-b", "employee-c"),
        allow_denied_capability=True,
    )
    assert req.requires_two_person is True
    assert req.risk_tier == "R4"
    assert req.status is ApprovalStatus.PENDING

    assert can_approve(bot, req) is False
    assert can_approve(requester, req) is False
    assert can_approve(first, req) is True

    still = resolve(req.approval_id, "employee-b", "approved")
    assert still.status is ApprovalStatus.PENDING
    assert still.approved_by == ["employee-b"]

    done = resolve(req.approval_id, "employee-c", "approved")
    assert done.status is ApprovalStatus.APPROVED
    assert set(done.approved_by) == {"employee-b", "employee-c"}


def test_expired_approval_cannot_be_approved():
    ctx = _ctx("employee-a", ["all-employees", "revenue", "executive"])
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    req = create_request(
        ctx,
        capability_id=Scope.CRM_OPPORTUNITY_UPDATE,
        params={"opportunity_id": "opp_2", "stage": "negotiation"},
        now=past - timedelta(hours=5),
        ttl=timedelta(hours=4),
    )
    assert req.expires_at is not None
    assert req.expires_at < datetime.now(timezone.utc)
    with pytest.raises(PermissionError, match="expired"):
        resolve(req.approval_id, "employee-b", "approved", now=datetime.now(timezone.utc))
    assert req.status is ApprovalStatus.EXPIRED


def test_duplicate_pending_request_rejected():
    ctx = _ctx("employee-a", ["all-employees", "revenue", "executive"])
    params = {"opportunity_id": "opp_3", "stage": "proposal"}
    first = create_request(ctx, Scope.CRM_OPPORTUNITY_UPDATE, params)
    with pytest.raises(ValueError, match="duplicate"):
        create_request(ctx, Scope.CRM_OPPORTUNITY_UPDATE, params)
    assert first.status is ApprovalStatus.PENDING


def test_service_cannot_request_or_self_approve_consequential():
    bot = service()
    ctx = _ctx("automation", ["automation"])
    assert can_request(bot, Scope.CRM_OPPORTUNITY_UPDATE, ["automation"]) is False
    with pytest.raises(PermissionError, match="automation"):
        create_request(ctx, Scope.CRM_OPPORTUNITY_UPDATE, {"opportunity_id": "opp_x"})


def test_policy_version_mismatch_rejected():
    ctx = _ctx("employee-a", ["all-employees", "revenue", "executive"])
    with pytest.raises(ValueError, match="policy_version"):
        create_request(
            ctx,
            Scope.CRM_OPPORTUNITY_UPDATE,
            {"opportunity_id": "opp_4"},
            policy_version="0.0.0-not-current",
        )


def test_denied_outcome_is_immutable():
    ctx = _ctx("employee-a", ["all-employees", "revenue", "executive"])
    req = create_request(
        ctx,
        Scope.CRM_OPPORTUNITY_UPDATE,
        {"opportunity_id": "opp_5", "stage": "hold"},
        named_approvers=("employee-b",),
    )
    denied = resolve(req.approval_id, "employee-b", "denied")
    assert denied.status is ApprovalStatus.DENIED
    with pytest.raises(PermissionError, match="immutable"):
        resolve(req.approval_id, "employee-c", "approved")
