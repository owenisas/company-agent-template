"""Approval request model (spec 12.4, 12.5, 36.2).

Approvals MUST be time-bound, action-specific, and invalidated when
material parameters change (spec 12.5 / §1059).

TODO: notification transport (D049). Named approver humans (D011–D018).
TODO: credential broker is Phase 4/5 — this package MUST NOT hold secrets.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    CONSUMED = "consumed"


class ApprovalRequest(BaseModel):
    """In-memory approval object. Outcomes are treated as immutable."""

    id: str = Field(default_factory=lambda: uuid4().hex)
    approval_id: str = Field(default_factory=lambda: f"apr_{uuid4().hex}")
    requester: str
    principal: str
    profile: str | None = None
    capability: str
    params_hash: str
    risk_tier: str
    approvers: tuple[str, ...] = Field(default_factory=tuple)
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: datetime
    expires_at: datetime
    approved_by: list[str] = Field(default_factory=list)
    requires_two_person: bool = False
    policy_version: str
    connection: str | None = None
    preview_hash: str | None = None
    reason: str = ""
    outcome_recorded: bool = False
