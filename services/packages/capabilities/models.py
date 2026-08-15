"""Typed capability records (spec 12.5, 36.1, Phase 3).

A capability is a named, versioned action class. It is NOT a credential.
Unknown capabilities MUST deny (spec 36.1 defaults).
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from packages.authz.scopes import RiskTier


class ApprovalMode(str, Enum):
    """Approval modes appearing in spec 36.1 / capabilities.yaml."""

    NONE = "none"
    KNOWLEDGE_OWNER = "knowledge-owner"
    REPOSITORY_PROTECTION = "repository-protection"
    RECORD_OWNER = "record-owner"
    NAMED = "named"
    TWO_PERSON = "two-person"
    CAMPAIGN_OWNER = "campaign-owner"


class Capability(BaseModel):
    """Registry row keyed by capability_id."""

    capability_id: str
    scope: str
    risk_tier: RiskTier
    allowed_toolset: tuple[str, ...] = Field(default_factory=tuple)
    external_write: bool = False
    approval_mode: ApprovalMode = ApprovalMode.NONE
    groups: frozenset[str] = Field(default_factory=frozenset)
    effect: str = "allow"
    preview_required: bool = False
    connections: tuple[str, ...] = Field(default_factory=tuple)

    model_config = {"frozen": True, "arbitrary_types_allowed": True}


class CapabilityDecision(BaseModel):
    """Outcome of capability_policy (deny by default)."""

    effect: str
    reason: str
    capability_id: str
    risk_tier: str | None = None

    @property
    def allowed(self) -> bool:
        return self.effect == "allow"
