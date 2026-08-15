"""Company-context connectors: refuse unconfigured, allowlist, no secrets."""

import pytest

from packages.connections.reference import contains_credential_value
from packages.connectors import (
    CONNECTOR_REGISTRY,
    DEFAULT_CONNECTOR,
    DEFAULT_NOTION_CONNECTOR,
    FUTURE_CONNECTORS,
)
from packages.connectors.notion_readonly import (
    PAGE_READ_FIELDS,
    TOOL_SCHEMAS,
    NotionReadOnlyConnector,
    allowlist_fields,
)
from packages.knowledge.ingestion import ingest_from_connector
from packages.tracing.context import RequestContext


def _ctx() -> RequestContext:
    return RequestContext(
        trace_id="trc_conn",
        request_id="req_conn",
        principal_id="employee-a",
        profile_id="employee-a",
        memberships=["all-employees"],
        release_id="scaffold",
        purpose="connector-test",
    )


def test_notion_tools_refuse_without_request_context():
    connector = NotionReadOnlyConnector()
    with pytest.raises(ValueError, match="RequestContext"):
        connector.invoke("pages.list", None, {"scope_id": "ws_1"})  # type: ignore[arg-type]


def test_notion_tools_refuse_when_unconfigured():
    connector = NotionReadOnlyConnector()
    assert connector.configured is False
    result = connector.invoke("page.read", _ctx(), {"page_id": "pg_1"})
    assert result.status == "not_configured"
    assert result.configured is False
    assert "D025" in result.detail
    assert result.payload["fields"] == list(TOOL_SCHEMAS["page.read"]["fields"])


def test_unknown_notion_action_is_denied():
    result = DEFAULT_NOTION_CONNECTOR.invoke("page.write", _ctx(), {})
    assert result.status == "deny"
    assert result.detail == "unknown_capability"


def test_field_allowlist_enforced():
    raw = {
        "id": "pg_1",
        "title": "Notes",
        "parent_id": "db_1",
        "last_edited_time": "2026-01-01T00:00:00Z",
        "url": "https://www.notion.so/example",
        "plain_text": "hello",
        "token": "should-not-pass",
        "api_key": "should-not-pass",
        "extra": "drop-me",
    }
    filtered = allowlist_fields(raw, PAGE_READ_FIELDS)
    assert set(filtered) == set(PAGE_READ_FIELDS)
    assert "token" not in filtered
    assert "api_key" not in filtered
    assert "extra" not in filtered


def test_no_credential_value_in_any_connector_object():
    objects = [
        DEFAULT_CONNECTOR,
        DEFAULT_NOTION_CONNECTOR,
        NotionReadOnlyConnector(),
        CONNECTOR_REGISTRY,
        FUTURE_CONNECTORS,
        TOOL_SCHEMAS,
    ]
    for obj in objects:
        dumped = obj if isinstance(obj, (dict, tuple, list, str)) else obj.__dict__
        assert contains_credential_value(dumped) is False
        assert not hasattr(obj, "token")
        assert not hasattr(obj, "api_key")
        assert not hasattr(obj, "secret")


def test_ingest_from_connector_dry_run_with_docs():
    report = ingest_from_connector(
        "notion_readonly",
        owner_principal_id="employee-a",
        documents=[{"title": "Standup", "plain_text": "Shipped the importer stub."}],
        dry_run=True,
    )
    assert report["status"] == "dry_run"
    assert report["connector_id"] == "notion_readonly"
    assert report["count"] == 1
    assert report["provenance"]["instruction_trust"] == "none"
    assert report["configured"] is False


def test_ingest_from_connector_without_docs_is_not_configured():
    report = ingest_from_connector("notion_readonly", owner_principal_id="employee-a")
    assert report["status"] == "not_configured"
    assert "D025" in report["detail"]
    assert report["dry_run"] is True
