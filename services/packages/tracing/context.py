"""RequestContext (spec 13.3) and propagation stubs.

Every request SHOULD contain trace_id, request_id, principal_id, profile_id,
memberships, task_id, release_id, purpose. Prompt/note content MUST NOT
modify authorization configuration (spec 13.4).
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class RequestContext(BaseModel):
    trace_id: str
    request_id: str
    principal_id: str
    profile_id: str | None = None
    memberships: list[str] = Field(default_factory=list)
    task_id: str | None = None
    release_id: str
    purpose: str

    @classmethod
    def require(cls, value: Any) -> "RequestContext":
        if not isinstance(value, RequestContext):
            raise ValueError("RequestContext required (spec 13.3)")
        value.assert_complete()
        return value

    def assert_complete(self) -> None:
        missing = [
            name
            for name in ("trace_id", "request_id", "principal_id", "release_id", "purpose")
            if not getattr(self, name)
        ]
        if missing:
            raise ValueError(f"RequestContext missing {missing} (spec 13.3)")


_current: ContextVar[RequestContext | None] = ContextVar("request_context", default=None)


def new_ids() -> tuple[str, str]:
    return uuid4().hex, uuid4().hex


def bind_context(ctx: RequestContext) -> None:
    """In-process propagation stub. Cross-service headers are TODO (Phase 3)."""
    RequestContext.require(ctx)
    _current.set(ctx)


def current_context() -> RequestContext | None:
    return _current.get()


def clear_context() -> None:
    _current.set(None)


def context_from_headers(headers: dict[str, str]) -> RequestContext | None:
    """Propagation stub: read conventional headers if present."""
    principal = headers.get("x-principal-id")
    if not principal:
        return None
    return RequestContext(
        trace_id=headers.get("x-trace-id") or uuid4().hex,
        request_id=headers.get("x-request-id") or uuid4().hex,
        principal_id=principal,
        profile_id=headers.get("x-profile-id"),
        memberships=[m for m in headers.get("x-memberships", "").split(",") if m],
        task_id=headers.get("x-task-id"),
        release_id=headers.get("x-release-id") or "scaffold",
        purpose=headers.get("x-purpose") or "unspecified",
    )
