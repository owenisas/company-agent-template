"""approval-api process (spec 12.4, 12.5, 13.2, 36.2).

Credential-free approval service skeleton:
  create → validate → time-bound/action-specific → resolve → immutable outcome.

TODO: notification service key (D049).
TODO: named approver humans (D011–D018).
TODO: credential broker MUST NOT be implemented here (spec 12.4).
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from packages.approval.service import create_request, get_request, resolve
from packages.tracing.context import RequestContext


class CreateApprovalBody(BaseModel):
    capability: str
    params: dict[str, Any] = Field(default_factory=dict)
    named_approvers: list[str] = Field(default_factory=list)
    connection: str | None = None
    preview_hash: str | None = None
    principal_id: str | None = None
    profile_id: str | None = None
    memberships: list[str] = Field(default_factory=list)
    trace_id: str | None = None
    request_id: str | None = None
    release_id: str = "scaffold"
    purpose: str = "approval.request"


class ResolveBody(BaseModel):
    actor: str
    decision: str


def _ctx_from_body(body: CreateApprovalBody) -> RequestContext:
    if not body.principal_id:
        raise HTTPException(status_code=400, detail="principal_id required")
    return RequestContext(
        trace_id=body.trace_id or "trc_unspecified",
        request_id=body.request_id or "req_unspecified",
        principal_id=body.principal_id,
        profile_id=body.profile_id,
        memberships=body.memberships,
        release_id=body.release_id,
        purpose=body.purpose,
    )


def create_app() -> FastAPI:
    app = FastAPI(
        title="<Company> approval-api",
        version="0.3.0-scaffold",
        description="Phase 3 scaffold. Notification transport not configured (D049).",
    )

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "approval-api",
            "notifications_configured": False,
            "credential_broker_configured": False,
            "detail": "TODO: D049 approval UX; D011-D018 named approvers; no broker",
        }

    @app.post("/approvals")
    def post_approval(body: CreateApprovalBody) -> dict[str, Any]:
        ctx = _ctx_from_body(body)
        try:
            req = create_request(
                ctx,
                body.capability,
                body.params,
                named_approvers=tuple(body.named_approvers),
                preview_hash=body.preview_hash,
                connection=body.connection,
            )
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return req.model_dump(mode="json")

    @app.get("/approvals/{approval_id}")
    def get_approval(approval_id: str) -> dict[str, Any]:
        req = get_request(approval_id)
        if req is None:
            return {"status": "not_found", "approval_id": approval_id}
        return req.model_dump(mode="json")

    @app.post("/approvals/{approval_id}/resolve")
    def post_resolve(approval_id: str, body: ResolveBody) -> dict[str, Any]:
        if get_request(approval_id) is None:
            raise HTTPException(status_code=404, detail="not_found")
        try:
            req = resolve(approval_id, body.actor, body.decision)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return req.model_dump(mode="json")

    return app


app = create_app()


def main() -> None:
    print(
        {
            "service": "approval-api",
            "status": "scaffold",
            "detail": "TODO: D049; D011-D018; do not start this process in Phase 3 scaffold",
        }
    )


if __name__ == "__main__":
    main()
