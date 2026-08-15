"""Capability registry deny-by-default (spec 36.1, Phase 3)."""

from packages.authz.scopes import RiskTier, Scope
from packages.capabilities.registry import (
    POLICY_VERSION,
    capability_policy,
    get_capability,
    list_capability_ids,
)


def test_unknown_capability_denied_by_default():
    decision = capability_policy("no.such.capability")
    assert decision.effect == "deny"
    assert decision.reason == "unknown_capability"
    assert decision.allowed is False
    assert get_capability("no.such.capability") is None


def test_registered_read_capability_is_present():
    cap = get_capability(Scope.KNOWLEDGE_SEARCH)
    assert cap is not None
    assert cap.capability_id == Scope.KNOWLEDGE_SEARCH
    assert cap.risk_tier is RiskTier.R0
    assert cap.external_write is False
    assert cap.approval_mode == "none"


def test_external_write_defaults_to_approval_required_effect():
    cap = get_capability(Scope.CRM_OPPORTUNITY_UPDATE)
    assert cap is not None
    assert cap.external_write is True
    assert cap.preview_required is True
    decision = capability_policy(Scope.CRM_OPPORTUNITY_UPDATE)
    assert decision.effect == "approval_required"


def test_signing_remains_denied():
    decision = capability_policy(Scope.CONTRACTS_SIGN)
    assert decision.effect == "deny"
    cap = get_capability(Scope.CONTRACTS_SIGN)
    assert cap is not None
    assert cap.risk_tier is RiskTier.R4
    assert cap.approval_mode == "two-person"


def test_registry_policy_version_matches_bundle():
    assert POLICY_VERSION == "1.0.0"
    assert Scope.GITHUB_READ in list_capability_ids()
    assert Scope.CRM_ACCOUNT_READ in list_capability_ids()
