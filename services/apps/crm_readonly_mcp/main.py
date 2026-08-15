"""CRM read-only MCP (spec 13.2 connector MCPs, §3876 narrow typed tools).

No credentials. No concrete API calls. Every tool requires RequestContext
and returns a structured not-configured result.
"""

from __future__ import annotations

from typing import Any

from packages.connectors.crm_readonly import TOOL_SCHEMAS
from packages.tracing.context import RequestContext

TOOLS = ("record.read", "stage.get", "renewal.read")

_NOT_CONFIGURED = "not_configured — D020/D021"


def _assert_ctx(ctx: RequestContext | None) -> RequestContext:
    return RequestContext.require(ctx)


def _result(tool: str, ctx: RequestContext, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    schema = TOOL_SCHEMAS.get(tool, {})
    body: dict[str, Any] = {
        "tool": tool,
        "status": "not_configured",
        "configured": False,
        "detail": _NOT_CONFIGURED,
        "trace_id": ctx.trace_id,
        "fields": list(schema.get("fields", ())),
    }
    if extra:
        body.update(extra)
    return body


def record_read(ctx: RequestContext | None, record_id: str) -> dict[str, Any]:
    ctx = _assert_ctx(ctx)
    return _result("record.read", ctx, {"record_id": record_id})


def stage_get(ctx: RequestContext | None, opportunity_id: str) -> dict[str, Any]:
    ctx = _assert_ctx(ctx)
    return _result("stage.get", ctx, {"opportunity_id": opportunity_id})


def renewal_read(ctx: RequestContext | None, account_id: str) -> dict[str, Any]:
    ctx = _assert_ctx(ctx)
    return _result("renewal.read", ctx, {"account_id": account_id})


HANDLERS = {
    "record.read": record_read,
    "stage.get": stage_get,
    "renewal.read": renewal_read,
}


def dispatch(tool: str, ctx: RequestContext | None, **kwargs: Any) -> dict[str, Any]:
    if tool not in HANDLERS:
        return {"status": "deny", "reason": "unknown_capability", "tool": tool}
    return HANDLERS[tool](ctx, **kwargs)


def main() -> None:
    print(
        {
            "service": "crm-readonly-mcp",
            "status": "not_configured",
            "tools": list(TOOLS),
            "detail": "TODO: D020 CRM name + object/field scope",
        }
    )


if __name__ == "__main__":
    main()
