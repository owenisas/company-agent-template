"""Pure-function authorization (spec 36.1, 4.2, 15.6).

is_allowed(principal, memberships, scope, risk_tier, requires_two_person)
-> Decision

Defaults from policies/capabilities.yaml (spec 36.1):
  unknown_capability: deny
  unknown_connection: deny
  external_write: approval_required
  bulk_export: approval_required

Invariant: automation-never-impersonates — a service principal cannot hold
employee scopes (spec 15.3, 15.4, 15.6; action-approval-matrix §1).
"""

from __future__ import annotations

from typing import Iterable

from pydantic import BaseModel, Field

from packages.authz.principals import Principal, PrincipalType
from packages.authz.scopes import (
    EMPLOYEE_PRIVATE_SCOPES,
    RiskTier,
    Scope,
    WRITE_SCOPES_BY_TIER,
    is_employee_scope,
    owner_slug_from_user_scope,
)

# Spec 36.1 defaults.
UNKNOWN_CAPABILITY_EFFECT = "deny"
UNKNOWN_CONNECTION_EFFECT = "deny"
EXTERNAL_WRITE_EFFECT = "approval_required"
BULK_EXPORT_EFFECT = "approval_required"

# Spec 36.1 capability table (groups + effect). Unknown -> deny.
CAPABILITIES: dict[str, dict] = {
    Scope.KNOWLEDGE_SEARCH: {
        "risk": RiskTier.R0,
        "groups": frozenset({"all-employees"}),
        "approval": "none",
        "effect": "allow",
    },
    Scope.KNOWLEDGE_RETRIEVE_SOURCE: {
        "risk": RiskTier.R0,
        "groups": frozenset({"all-employees"}),
        "approval": "none",
        "effect": "allow",
    },
    Scope.KNOWLEDGE_INGEST_DRY_RUN: {
        "risk": RiskTier.R0,
        "groups": frozenset({"all-employees", "agent-builders", "automation"}),
        "approval": "none",
        "effect": "allow",
    },
    Scope.KNOWLEDGE_INGEST: {
        "risk": RiskTier.R1,
        "groups": frozenset({"all-employees"}),
        "approval": "none",
        "effect": "allow",
    },
    Scope.KNOWLEDGE_PROMOTE_CLAIM: {
        "risk": RiskTier.R2,
        "groups": frozenset({"research", "executive"}),
        "approval": "knowledge-owner",
        "effect": "approval_required",
    },
    Scope.KNOWLEDGE_FORGET: {
        "risk": RiskTier.R3,
        "groups": frozenset({"agent-platform-admins"}),
        "approval": "named",
        "effect": "approval_required",
    },
    Scope.GITHUB_READ: {
        "risk": RiskTier.R0,
        "groups": frozenset({"all-employees", "engineering", "automation"}),
        "approval": "none",
        "effect": "allow",
    },
    Scope.GITHUB_PR_CREATE: {
        "risk": RiskTier.R2,
        "groups": frozenset({"engineering"}),
        "approval": "none",
        "effect": "allow",
    },
    Scope.GITHUB_PROTECTED_MERGE: {
        # R3 (high). Matrix §3 Deploy / production — not R4 (signing/payment).
        "risk": RiskTier.R3,
        "groups": frozenset({"engineering"}),
        "approval": "repository-protection",
        "effect": "approval_required",
    },
    Scope.CRM_ACCOUNT_READ: {
        "risk": RiskTier.R0,
        "groups": frozenset({"revenue", "customer-success", "executive"}),
        "approval": "none",
        "effect": "allow",
    },
    Scope.CRM_OPPORTUNITY_UPDATE: {
        "risk": RiskTier.R3,
        "groups": frozenset({"revenue", "executive"}),
        "approval": "record-owner",
        "effect": "approval_required",
    },
    Scope.CRM_BULK_EXPORT: {
        "risk": RiskTier.R3,
        "groups": frozenset({"customer-data-approvers", "executive"}),
        "approval": "named",
        "effect": "approval_required",
    },
    Scope.PUBLISHING_SEND: {
        "risk": RiskTier.R2,
        "groups": frozenset({"marketing", "executive"}),
        "approval": "campaign-owner",
        "effect": "approval_required",
    },
    Scope.CONTRACTS_SIGN: {
        "risk": RiskTier.R4,
        "groups": frozenset(),
        "approval": "two-person",
        "effect": "deny",
    },
    Scope.FINANCE_PAYMENT: {
        "risk": RiskTier.R4,
        "groups": frozenset(),
        "approval": "two-person",
        "effect": "deny",
    },
    Scope.IDENTITY_IMPERSONATE: {
        "risk": RiskTier.R4,
        "groups": frozenset(),
        "approval": "none",
        "effect": "deny",
    },
    Scope.APPROVAL_DECIDE: {
        "risk": RiskTier.R3,
        "groups": frozenset(
            {
                "legal-approvers",
                "finance-approvers",
                "agent-platform-admins",
                "people-hr-approvers",
                "customer-data-approvers",
            }
        ),
        "approval": "named",
        "effect": "allow",
    },
    Scope.NOTION_READ_PAGE: {
        "risk": RiskTier.R0,
        "groups": frozenset({"all-employees"}),
        "approval": "none",
        "effect": "allow",
    },
    Scope.NOTION_SEARCH: {
        "risk": RiskTier.R0,
        "groups": frozenset({"all-employees"}),
        "approval": "none",
        "effect": "allow",
    },
    Scope.NOTION_QUERY_DATABASE: {
        "risk": RiskTier.R0,
        "groups": frozenset({"all-employees"}),
        "approval": "none",
        "effect": "allow",
    },
    Scope.NOTION_CREATE_PAGE: {
        "risk": RiskTier.R2,
        "groups": frozenset({"all-employees"}),
        "approval": "named",
        "effect": "approval_required",
    },
    Scope.NOTION_APPEND_BLOCKS: {
        "risk": RiskTier.R2,
        "groups": frozenset({"all-employees"}),
        "approval": "named",
        "effect": "approval_required",
    },
    Scope.NOTION_UPDATE_PAGE_PROPERTY: {
        "risk": RiskTier.R2,
        "groups": frozenset({"all-employees"}),
        "approval": "named",
        "effect": "approval_required",
    },
}

KNOWN_CONNECTIONS: frozenset[str] = frozenset(
    {
        Scope.CONN_KNOWLEDGE,
        Scope.CONN_POSTGRES,
        Scope.CONN_RAW_OBJECTS,
        Scope.CONN_KNOWLEDGE_MCP,
        Scope.CONN_APPROVAL_API,
        Scope.CONN_GITHUB_BOT,
        Scope.CONN_GITHUB_OAUTH_PREFIX,
        Scope.CONN_CRM_READONLY,
        Scope.CONN_CRM_WRITE,
        Scope.CONN_CONTRACTS,
        Scope.CONN_FINANCE,
        Scope.CONN_EMAIL,
        Scope.CONN_SOCIAL,
        Scope.CONN_DISCORD,
        Scope.CONN_NOTION_OAUTH,
        Scope.CONN_NOTION_OAUTH_PREFIX,
    }
)

_CONNECTION_PREFIXES = ("company/", "team:", "user:")


class Decision(BaseModel):
    effect: str = Field(description="allow | deny | approval_required")
    reason: str
    scope: str
    risk_tier: str
    requires_two_person: bool = False

    @property
    def allowed(self) -> bool:
        return self.effect == "allow"


def _normalize_tier(risk_tier: RiskTier | str) -> RiskTier:
    if isinstance(risk_tier, RiskTier):
        return risk_tier
    value = str(risk_tier).upper()
    return RiskTier(value if value.startswith("R") else f"R{value}")


def _is_connection_scope(scope: str) -> bool:
    return scope.startswith(_CONNECTION_PREFIXES) or scope in KNOWN_CONNECTIONS


def is_allowed(
    principal: Principal,
    memberships: Iterable[str],
    scope: str,
    risk_tier: RiskTier | str,
    requires_two_person: bool,
) -> Decision:
    """Return an authorization Decision. Defaults deny / deny / approval_required."""
    tier = _normalize_tier(risk_tier)
    groups = frozenset(memberships)
    two = bool(requires_two_person)

    if not principal.active:
        return Decision(
            effect="deny",
            reason="principal_inactive",
            scope=scope,
            risk_tier=tier.value,
            requires_two_person=two,
        )

    # --- invariant: service MUST NOT hold employee scopes (spec 15.6) ---
    if principal.principal_type is PrincipalType.SERVICE and is_employee_scope(scope):
        return Decision(
            effect="deny",
            reason="automation_never_impersonates",
            scope=scope,
            risk_tier=tier.value,
            requires_two_person=two,
        )

    # Employee A cannot read employee B private/restricted scope.
    if scope in EMPLOYEE_PRIVATE_SCOPES or (
        scope.startswith("user:") and owner_slug_from_user_scope(scope)
    ):
        owner = owner_slug_from_user_scope(scope)
        if principal.principal_type is PrincipalType.SYSTEM:
            return Decision(
                effect="allow",
                reason="system_control_plane",
                scope=scope,
                risk_tier=tier.value,
                requires_two_person=two,
            )
        if principal.slug != owner:
            return Decision(
                effect="deny",
                reason="cross_user_restricted_denied",
                scope=scope,
                risk_tier=tier.value,
                requires_two_person=two,
            )
        return Decision(
            effect="allow",
            reason="owner_self_scope",
            scope=scope,
            risk_tier=tier.value,
            requires_two_person=two,
        )

    if _is_connection_scope(scope) and scope not in KNOWN_CONNECTIONS:
        return Decision(
            effect=UNKNOWN_CONNECTION_EFFECT,
            reason="unknown_connection",
            scope=scope,
            risk_tier=tier.value,
            requires_two_person=two,
        )

    cap = CAPABILITIES.get(scope)
    if cap is None:
        # Known write scopes still follow tier defaults; truly unknown deny.
        known_writes = set().union(*WRITE_SCOPES_BY_TIER.values())
        if scope not in known_writes:
            return Decision(
                effect=UNKNOWN_CAPABILITY_EFFECT,
                reason="unknown_capability",
                scope=scope,
                risk_tier=tier.value,
                requires_two_person=two,
            )
        if scope in {Scope.CRM_BULK_EXPORT}:
            return Decision(
                effect=BULK_EXPORT_EFFECT,
                reason="bulk_export_default",
                scope=scope,
                risk_tier=tier.value,
                requires_two_person=two,
            )
        if tier in {RiskTier.R2, RiskTier.R3, RiskTier.R4}:
            return Decision(
                effect=EXTERNAL_WRITE_EFFECT,
                reason="external_write_default",
                scope=scope,
                risk_tier=tier.value,
                requires_two_person=True if tier is RiskTier.R4 else two,
            )
        return Decision(
            effect="deny",
            reason="unknown_capability",
            scope=scope,
            risk_tier=tier.value,
            requires_two_person=two,
        )

    if cap.get("effect") == "deny":
        return Decision(
            effect="deny",
            reason="capability_denied",
            scope=scope,
            risk_tier=tier.value,
            requires_two_person=two,
        )

    allowed_groups: frozenset[str] = cap["groups"]
    if allowed_groups and groups.isdisjoint(allowed_groups):
        # Service is never in all-employees; do not grant via confused deputy.
        return Decision(
            effect="deny",
            reason="group_not_permitted",
            scope=scope,
            risk_tier=tier.value,
            requires_two_person=two,
        )

    if two or cap.get("approval") not in {None, "none"}:
        return Decision(
            effect="approval_required",
            reason="approval_required",
            scope=scope,
            risk_tier=tier.value,
            requires_two_person=two or cap.get("approval") == "two-person",
        )

    if principal.principal_type is PrincipalType.SERVICE and tier in {
        RiskTier.R2,
        RiskTier.R3,
        RiskTier.R4,
    }:
        return Decision(
            effect="approval_required",
            reason="automation_consequential_action",
            scope=scope,
            risk_tier=tier.value,
            requires_two_person=tier is RiskTier.R4,
        )

    return Decision(
        effect="allow",
        reason="capability_allow",
        scope=scope,
        risk_tier=tier.value,
        requires_two_person=False,
    )
