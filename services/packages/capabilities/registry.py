"""Capability registry (spec 36.1 defaults, Phase 3 deliverable).

Seeded from policies/capabilities.yaml concepts plus the Phase 2
packages.authz.policy.CAPABILITIES table so tiers stay consistent.

Defaults (MUST):
  unknown_capability: deny
  unknown_connection: deny
  external_write: approval_required
  bulk_export: approval_required

TODO: live policy-bundle load from distribution (D057/D058 adjacent;
named groups remain D008–D014).
"""

from __future__ import annotations

from packages.authz.policy import CAPABILITIES, EXTERNAL_WRITE_EFFECT
from packages.authz.scopes import RiskTier, Scope
from packages.capabilities.models import ApprovalMode, Capability, CapabilityDecision

POLICY_VERSION = "1.0.0"

# Narrow toolsets for Phase 3 shared read-only MCPs (spec 13.2, §3876).
_GITHUB_READ_TOOLS = ("repo.metadata", "file.read", "issues.list")
_CRM_READ_TOOLS = ("record.read", "stage.get", "renewal.read")

_YAML_CONNECTIONS: dict[str, tuple[str, ...]] = {
    Scope.KNOWLEDGE_SEARCH: ("company/knowledge",),
    Scope.GITHUB_PR_CREATE: ("user:*/github-oauth", "company/github-hermes-bot"),
    Scope.CRM_ACCOUNT_READ: ("company/crm-readonly",),
    Scope.CRM_OPPORTUNITY_UPDATE: ("user:*/crm-oauth", "team:revenue/crm-automation"),
    Scope.PUBLISHING_SEND: ("company/email-platform", "company/social-brand"),
}

_TOOLSETS: dict[str, tuple[str, ...]] = {
    Scope.GITHUB_READ: _GITHUB_READ_TOOLS,
    Scope.CRM_ACCOUNT_READ: _CRM_READ_TOOLS,
}

_PREVIEW_REQUIRED = frozenset(
    {
        Scope.CRM_OPPORTUNITY_UPDATE,
        Scope.PUBLISHING_SEND,
        Scope.CRM_BULK_EXPORT,
        Scope.CONTRACTS_SIGN,
        Scope.FINANCE_PAYMENT,
        Scope.GITHUB_PROTECTED_MERGE,
    }
)

_EXTERNAL_WRITE = frozenset(
    {
        Scope.GITHUB_PR_CREATE,
        Scope.GITHUB_PROTECTED_MERGE,
        Scope.CRM_OPPORTUNITY_UPDATE,
        Scope.CRM_BULK_EXPORT,
        Scope.PUBLISHING_SEND,
        Scope.CONTRACTS_SIGN,
        Scope.FINANCE_PAYMENT,
        Scope.DISCORD_SEND,
        Scope.KNOWLEDGE_FORGET,
    }
)


def _mode_from_cap(raw: dict) -> ApprovalMode:
    value = str(raw.get("approval") or "none")
    try:
        return ApprovalMode(value)
    except ValueError:
        return ApprovalMode.NAMED


def _build_registry() -> dict[str, Capability]:
    registry: dict[str, Capability] = {}
    for scope, raw in CAPABILITIES.items():
        risk: RiskTier = raw["risk"]
        effect = str(raw.get("effect") or "allow")
        external = scope in _EXTERNAL_WRITE
        if external and effect == "allow":
            # Spec 36.1 default: external_write -> approval_required.
            effect = EXTERNAL_WRITE_EFFECT
        registry[scope] = Capability(
            capability_id=scope,
            scope=scope,
            risk_tier=risk,
            allowed_toolset=_TOOLSETS.get(scope, (scope,)),
            external_write=external,
            approval_mode=_mode_from_cap(raw),
            groups=frozenset(raw.get("groups") or ()),
            effect=effect,
            preview_required=scope in _PREVIEW_REQUIRED or external,
            connections=_YAML_CONNECTIONS.get(scope, ()),
        )
    return registry


REGISTRY: dict[str, Capability] = _build_registry()


def list_capability_ids() -> frozenset[str]:
    return frozenset(REGISTRY)


def get_capability(capability_id: str) -> Capability | None:
    return REGISTRY.get(capability_id)


def capability_policy(capability_id: str) -> CapabilityDecision:
    """Reject any capability outside the registry (deny by default)."""
    cap = REGISTRY.get(capability_id)
    if cap is None:
        return CapabilityDecision(
            effect="deny",
            reason="unknown_capability",
            capability_id=capability_id,
        )
    return CapabilityDecision(
        effect=cap.effect,
        reason="registered" if cap.effect == "allow" else cap.effect,
        capability_id=capability_id,
        risk_tier=cap.risk_tier.value,
    )
