"""knowledge-api process (spec 13.2, 13.4).

Authenticated document, claim, research, and admin API.
Phase 2 scaffold: no secrets, no live DB. App factory reads config via
spec 13.4 layering. Routers return not-configured / TODO.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse

from packages.config import Settings, load_config
from packages.tracing.context import RequestContext, context_from_headers

health_router = APIRouter(tags=["health"])
docs_router = APIRouter(prefix="/docs-api", tags=["docs"])
claims_router = APIRouter(prefix="/claims", tags=["claims"])
research_router = APIRouter(prefix="/research", tags=["research"])
admin_router = APIRouter(prefix="/admin", tags=["admin"])


def _not_configured(what: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {
        "status": "not_configured",
        "configured": False,
        "resource": what,
        "detail": f"TODO: {what} requires D055 postgres host and D040 embeddings",
    }
    if extra:
        body.update(extra)
    return body


@health_router.get("/health")
def health(request: Request) -> dict[str, Any]:
    cfg: Settings = request.app.state.config
    return {
        "status": "ok",
        "service": "knowledge-api",
        "phase": "2-scaffold",
        "database_configured": cfg.database_configured,
        "embeddings_configured": cfg.embeddings_configured,
    }


@docs_router.get("/sources/{source_id}")
def get_source(source_id: str) -> dict[str, Any]:
    return _not_configured("source_retrieve", {"source_id": source_id})


@docs_router.post("/ingest")
def ingest_stub() -> dict[str, Any]:
    return _not_configured("ingest")


@claims_router.get("")
def list_claims() -> dict[str, Any]:
    return _not_configured("claims")


@claims_router.post("/propose")
def propose_claim() -> dict[str, Any]:
    return _not_configured("claim_propose")


@research_router.get("/packets/{packet_id}")
def get_packet(packet_id: str) -> dict[str, Any]:
    return _not_configured("research_packet", {"packet_id": packet_id})


@research_router.post("/packets")
def create_packet() -> dict[str, Any]:
    return _not_configured("research_packet_create")


@admin_router.get("/status")
def admin_status() -> dict[str, Any]:
    return _not_configured("admin")


def create_app(config: Settings | None = None) -> FastAPI:
    """App factory. Config via spec 13.4; no secrets loaded from disk besides refs."""
    cfg = config or load_config()
    app = FastAPI(
        title="<Company> knowledge-api",
        version="0.2.0-scaffold",
        description="Phase 2 scaffold — credential-free. MUST NOT hold connector secrets (spec 13.2).",
    )
    app.state.config = cfg
    app.include_router(health_router)
    app.include_router(docs_router)
    app.include_router(claims_router)
    app.include_router(research_router)
    app.include_router(admin_router)

    @app.middleware("http")
    async def attach_context(request: Request, call_next):  # type: ignore[no-untyped-def]
        ctx = context_from_headers(dict(request.headers))
        request.state.ctx = ctx
        return await call_next(request)

    @app.get("/")
    def root() -> dict[str, Any]:
        return {"service": "knowledge-api", "status": "scaffold"}

    return app


app = create_app()


def require_ctx(request: Request) -> RequestContext:
    ctx = getattr(request.state, "ctx", None)
    return RequestContext.require(ctx)


@app.exception_handler(ValueError)
async def _value_error(_request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse({"status": "error", "detail": str(exc)}, status_code=400)
