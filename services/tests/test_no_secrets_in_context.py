"""Shared credentials never enter Hermes context (Phase 3 exit)."""

from packages.actions.preview_apply import preview
from packages.approval.tamper import request_fingerprint
from packages.capabilities.registry import get_capability, list_capability_ids
from packages.connections.models import ConnectionReference, CredentialClass
from packages.connections.reference import contains_credential_value, resolve_reference
from packages.tracing.context import RequestContext


def test_no_capability_object_contains_a_credential_value():
    for capability_id in list_capability_ids():
        cap = get_capability(capability_id)
        assert cap is not None
        assert contains_credential_value(cap.model_dump()) is False


def test_connection_and_handle_never_embed_credential_value():
    ref = ConnectionReference(
        id="company/github-hermes-bot",
        plugin="github",
        scope="company",
        principal="github-app:UNCONFIGURED",
        credential_ref="secret://company/github/company-bot",
        credential_class=CredentialClass.SHARED,
        allowed_actions=("repository.read",),
        forbidden_actions=("repository.delete",),
        approval_policy="none_for_allowed_actions",
        owner="TODO: D051",
    )
    handle = resolve_reference(ref, action="repository.read")
    assert contains_credential_value(ref.model_dump()) is False
    assert contains_credential_value(handle.model_dump()) is False
    assert "credential_ref" not in handle.model_dump()


def test_preview_and_fingerprint_inputs_drop_secret_like_keys():
    ctx = RequestContext(
        trace_id="trc_secret",
        request_id="req_secret",
        principal_id="employee-a",
        profile_id="employee-a",
        memberships=["all-employees", "revenue", "executive"],
        release_id="scaffold",
        purpose="secret-scan",
    )
    params = {
        "opportunity_id": "opp_1",
        "stage": "won",
        "api_key": "should-be-stripped",
        "password": "should-be-stripped",
        "token": "should-be-stripped",
    }
    p = preview("crm.opportunity.update", params, ctx)
    assert contains_credential_value(p.model_dump()) is False
    assert "should-be-stripped" not in p.effect_description
    assert "should-be-stripped" not in p.params_fingerprint
    assert "api_key" not in p.params
    dumped = request_fingerprint(
        {
            "capability": "crm.opportunity.update",
            "params": p.params,
            "principal": "employee-a",
            "connection": None,
            "policy_version": "1.0.0",
            "risk_tier": "R3",
        }
    )
    assert "should-be-stripped" not in dumped
