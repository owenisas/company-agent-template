"""GitHub read-only MCP (spec 13.2 connector MCPs, §3876 narrow typed tools).

No credentials. No concrete API calls. Every tool requires RequestContext
and returns a structured not-configured result.
"""

from __future__ import annotations

from typing import Any

from packages.connectors.github_readonly import TOOL_SCHEMAS
from packages.tracing.context import RequestContext

TOOLS = ("repo.metadata", "file.read", "issues.list")

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


def repo_metadata(ctx: RequestContext | None, owner: str, repo: str) -> dict[str, Any]:
    ctx = _assert_ctx(ctx)
    return _result("repo.metadata", ctx, {"owner": owner, "repo": repo})


def file_read(
    ctx: RequestContext | None,
    owner: str,
    repo: str,
    path: str,
    ref: str | None = None,
) -> dict[str, Any]:
    ctx = _assert_ctx(ctx)
    return _result("file.read", ctx, {"owner": owner, "repo": repo, "path": path, "ref": ref})


def issues_list(
    ctx: RequestContext | None,
    owner: str,
    repo: str,
    state: str = "open",
) -> dict[str, Any]:
    ctx = _assert_ctx(ctx)
    return _result("issues.list", ctx, {"owner": owner, "repo": repo, "state": state})


HANDLERS = {
    "repo.metadata": repo_metadata,
    "file.read": file_read,
    "issues.list": issues_list,
}


def dispatch(tool: str, ctx: RequestContext | None, **kwargs: Any) -> dict[str, Any]:
    if tool not in HANDLERS:
        return {"status": "deny", "reason": "unknown_capability", "tool": tool}
    return HANDLERS[tool](ctx, **kwargs)


def main() -> None:
    print(
        {
            "service": "github-readonly-mcp",
            "status": "not_configured",
            "tools": list(TOOLS),
            "detail": "TODO: D042/D051 GitHub org + app owner; D020/D021 listed as connector-scope pair",
        }
    )


if __name__ == "__main__":
    main()
