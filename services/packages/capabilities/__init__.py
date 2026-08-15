"""Capabilities package (spec 36.1, Phase 3)."""

from packages.capabilities.models import ApprovalMode, Capability, CapabilityDecision
from packages.capabilities.registry import (
    POLICY_VERSION,
    REGISTRY,
    capability_policy,
    get_capability,
)

__all__ = [
    "ApprovalMode",
    "Capability",
    "CapabilityDecision",
    "POLICY_VERSION",
    "REGISTRY",
    "capability_policy",
    "get_capability",
]
