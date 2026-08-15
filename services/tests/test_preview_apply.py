"""Preview-before-apply ordering (spec 12.2, 12.5, 30.3)."""

import pytest

from packages.actions.preview_apply import apply, apply_requires_approval, preview
from packages.approval.service import create_request, reset_store, resolve
from packages.authz.scopes import Scope
from packages.tracing.context import RequestContext


def _ctx() -> RequestContext:
    return RequestContext(
        trace_id="trc_preview",
        request_id="req_preview",
        principal_id="employee-a",
        profile_id="employee-a",
        memberships=["all-employees", "revenue", "executive"],
        release_id="scaffold",
        purpose="phase3-preview",
    )


def setup_function() -> None:
    reset_store()


def test_external_write_requires_approval():
    ctx = _ctx()
    p = preview(Scope.CRM_OPPORTUNITY_UPDATE, {"opportunity_id": "opp_1", "stage": "won"}, ctx)
    assert p.params_fingerprint.startswith("sha256:")
    assert "secret" not in p.effect_description.lower()
    assert apply_requires_approval(p) is True


def test_apply_without_preview_is_rejected():
    ctx = _ctx()
    with pytest.raises(PermissionError, match="preview"):
        apply(
            None,
            ctx,
            capability_id=Scope.CRM_OPPORTUNITY_UPDATE,
            params={"opportunity_id": "opp_1", "stage": "won"},
        )


def test_apply_without_matching_approved_preview_is_rejected():
    ctx = _ctx()
    p = preview(Scope.CRM_OPPORTUNITY_UPDATE, {"opportunity_id": "opp_1", "stage": "won"}, ctx)
    with pytest.raises(PermissionError, match="approval"):
        apply(p, ctx, capability_id=Scope.CRM_OPPORTUNITY_UPDATE, params=p.params)


def test_preview_approval_apply_succeeds_and_records_attribution():
    ctx = _ctx()
    params = {"opportunity_id": "opp_9", "stage": "won"}
    p = preview(Scope.CRM_OPPORTUNITY_UPDATE, params, ctx)
    req = create_request(
        ctx,
        Scope.CRM_OPPORTUNITY_UPDATE,
        params,
        named_approvers=("employee-b",),
        preview_hash=p.params_fingerprint,
    )
    resolve(req.approval_id, "employee-b", "approved")
    result = apply(
        p,
        ctx,
        capability_id=Scope.CRM_OPPORTUNITY_UPDATE,
        params=params,
        approval_id=req.approval_id,
    )
    assert result.status == "recorded"
    assert result.approval_id == req.approval_id
    assert result.attribution["requested_by"] == "employee-a"
    assert result.attribution["agent_profile"] == "employee-a"


def test_tampered_params_after_preview_are_rejected():
    ctx = _ctx()
    params = {"opportunity_id": "opp_10", "stage": "won"}
    p = preview(Scope.CRM_OPPORTUNITY_UPDATE, params, ctx)
    req = create_request(
        ctx,
        Scope.CRM_OPPORTUNITY_UPDATE,
        params,
        named_approvers=("employee-b",),
        preview_hash=p.params_fingerprint,
    )
    resolve(req.approval_id, "employee-b", "approved")
    with pytest.raises(PermissionError, match="fingerprint|tamper"):
        apply(
            p,
            ctx,
            capability_id=Scope.CRM_OPPORTUNITY_UPDATE,
            params={"opportunity_id": "opp_10", "stage": "lost"},
            approval_id=req.approval_id,
        )
