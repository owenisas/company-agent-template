"""knowledge-mcp process (spec 13.2, 27).

Tool surface for Phase 2 scaffold:
  knowledge.search
  knowledge.retrieve_source
  knowledge.ingest_dry_run

Stubs return structured not-configured results. Every tool asserts
RequestContext (spec 13.3). Service holds no user raw secrets.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from packages.authz.principals import parse_principal
from packages.knowledge.ingestion import bulk_import_dry_run
from packages.knowledge.retrieval import hybrid_search_stub
from packages.tracing.context import RequestContext


TOOLS = (
    "knowledge.search",
    "knowledge.retrieve_source",
    "knowledge.ingest_dry_run",
)


def _assert_ctx(ctx: RequestContext | None) -> RequestContext:
    return RequestContext.require(ctx)


def knowledge_search(ctx: RequestContext | None, query: str, mode: str = "hybrid") -> dict[str, Any]:
    ctx = _assert_ctx(ctx)
    principal = parse_principal(ctx.principal_id)
    result = hybrid_search_stub(principal, ctx.memberships, query)
    result.update(
        {
            "tool": "knowledge.search",
            "mode": mode,
            "trace_id": ctx.trace_id,
            "hits": [],
            "status": "not_configured",
        }
    )
    return result


def knowledge_retrieve_source(ctx: RequestContext | None, source_id: str, locator: str | None = None) -> dict[str, Any]:
    ctx = _assert_ctx(ctx)
    return {
        "tool": "knowledge.retrieve_source",
        "status": "not_configured",
        "configured": False,
        "source_id": source_id,
        "locator": locator,
        "trace_id": ctx.trace_id,
        "detail": "TODO: D055 postgres + ACL/RLS; will not return unauthorized excerpts",
    }


def knowledge_ingest_dry_run(ctx: RequestContext | None, items: list[dict[str, Any]]) -> dict[str, Any]:
    ctx = _assert_ctx(ctx)
    report = bulk_import_dry_run(items, owner_principal_id=ctx.principal_id)
    report.update({"tool": "knowledge.ingest_dry_run", "trace_id": ctx.trace_id})
    return report


HANDLERS = {
    "knowledge.search": knowledge_search,
    "knowledge.retrieve_source": knowledge_retrieve_source,
    "knowledge.ingest_dry_run": knowledge_ingest_dry_run,
}


def dispatch(tool: str, ctx: RequestContext | None, **kwargs: Any) -> dict[str, Any]:
    if tool not in HANDLERS:
        return {"status": "deny", "reason": "unknown_capability", "tool": tool}
    return HANDLERS[tool](ctx, **kwargs)


def create_app() -> FastAPI:
    """HTTP health surface so Compose can keep this process up (Phase 2)."""
    app = FastAPI(
        title="<Company> knowledge-mcp",
        version="0.2.0-scaffold",
        description="Phase 2 scaffold — tool dispatch is still in-process.",
    )

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "knowledge-mcp",
            "phase": "2-scaffold",
            "tools": list(TOOLS),
        }

    @app.get("/")
    def root() -> dict[str, Any]:
        return {"service": "knowledge-mcp", "status": "scaffold", "tools": list(TOOLS)}

    return app


app = create_app()


def main() -> None:
    print(
        {
            "service": "knowledge-mcp",
            "status": "not_configured",
            "tools": list(TOOLS),
            "detail": "TODO: MCP SDK transport (Phase 2 runtime, not this scaffold)",
        }
    )


if __name__ == "__main__":
    main()
