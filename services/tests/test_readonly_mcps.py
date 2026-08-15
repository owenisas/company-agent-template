"""Read-only GitHub/CRM MCP skeletons (spec 13.2, §3876)."""

import pytest

from apps.crm_readonly_mcp.main import TOOLS as CRM_TOOLS
from apps.crm_readonly_mcp.main import dispatch as crm_dispatch
from apps.github_readonly_mcp.main import TOOLS as GH_TOOLS
from apps.github_readonly_mcp.main import dispatch as gh_dispatch
from packages.tracing.context import RequestContext


def _ctx() -> RequestContext:
    return RequestContext(
        trace_id="trc_mcp",
        request_id="req_mcp",
        principal_id="employee-a",
        profile_id="employee-a",
        memberships=["all-employees", "engineering", "revenue"],
        release_id="scaffold",
        purpose="readonly-mcp",
    )


def test_github_tools_require_request_context_and_are_not_configured():
    assert GH_TOOLS == ("repo.metadata", "file.read", "issues.list")
    with pytest.raises(ValueError, match="RequestContext"):
        gh_dispatch("repo.metadata", None, owner="acme", repo="platform")
    result = gh_dispatch("repo.metadata", _ctx(), owner="acme", repo="platform")
    assert result["status"] == "not_configured"
    assert "D020/D021" in result["detail"]
    assert result["trace_id"] == "trc_mcp"
    assert "fields" in result


def test_crm_tools_require_request_context_and_are_not_configured():
    assert CRM_TOOLS == ("record.read", "stage.get", "renewal.read")
    with pytest.raises(ValueError, match="RequestContext"):
        crm_dispatch("record.read", None, record_id="acc_1")
    result = crm_dispatch("record.read", _ctx(), record_id="acc_1")
    assert result["status"] == "not_configured"
    assert "D020/D021" in result["detail"]
    assert result["configured"] is False
