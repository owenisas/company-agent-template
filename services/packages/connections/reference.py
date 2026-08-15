"""Resolve a connection reference to an opaque handle (spec 12.1, 12.3).

Resolution never returns the credential value. External writes require
an approvable (approved) action.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from pydantic import BaseModel

from packages.approval.models import ApprovalStatus
from packages.connections.models import ConnectionReference, CredentialClass

_READ_ACTIONS = frozenset(
    {
        "repository.read",
        "file.read",
        "issues.list",
        "repo.metadata",
        "accounts.read",
        "contacts.read",
        "opportunities.read",
        "record.read",
        "stage.get",
        "renewal.read",
    }
)

_CREDENTIAL_VALUE_RE = re.compile(
    r"(ghp_[A-Za-z0-9]+|sk-[A-Za-z0-9]+|crsr_[A-Za-z0-9]+|BEGIN [A-Z ]*PRIVATE KEY)",
    re.IGNORECASE,
)
_SECRET_FIELD_NAMES = frozenset(
    {"password", "passwd", "token", "api_key", "api-key", "apikey", "access_token", "refresh_token"}
)


class OpaqueHandle(BaseModel):
    """Server-side handle. MUST NOT include credential_ref or secret material."""

    handle_id: str
    connection_id: str
    credential_class: CredentialClass
    plugin: str
    allowed_actions: tuple[str, ...] = ()


def _handle_id(connection_id: str) -> str:
    digest = hashlib.sha256(connection_id.encode("utf-8")).hexdigest()[:16]
    return f"href_{digest}"


def resolve_reference(
    ref: ConnectionReference,
    action: str,
    *,
    approval_status: ApprovalStatus | None = None,
    approval_id: str | None = None,
) -> OpaqueHandle:
    """Resolve to an opaque handle. Never returns the credential value."""
    _ = approval_id
    if action in ref.forbidden_actions:
        raise PermissionError("forbidden_action")
    if ref.allowed_actions and action not in ref.allowed_actions:
        raise PermissionError("action_not_allowed")
    write = action not in _READ_ACTIONS
    if write and approval_status is not ApprovalStatus.APPROVED:
        raise PermissionError("approvable_action_required")
    return OpaqueHandle(
        handle_id=_handle_id(ref.id),
        connection_id=ref.id,
        credential_class=ref.credential_class,
        plugin=ref.plugin,
        allowed_actions=ref.allowed_actions,
    )


def contains_credential_value(payload: Any) -> bool:
    """True if a dumped object appears to embed a credential *value*."""
    return _walk(payload, field_name="")


def _walk(value: Any, field_name: str) -> bool:
    if isinstance(value, dict):
        return any(_walk(v, str(k)) for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return any(_walk(v, field_name) for v in value)
    if not isinstance(value, str):
        return False
    text = value.strip()
    if not text:
        return False
    if text.startswith("secret://"):
        return False
    if text.startswith("TODO:"):
        return False
    if _CREDENTIAL_VALUE_RE.search(text):
        return True
    if field_name.lower() in _SECRET_FIELD_NAMES:
        return True
    return False
