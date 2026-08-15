"""Notion collaboration tools: allowlist, not_configured, preview/apply, attribution."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from packages.approval.service import create_request, reset_store, resolve
from packages.authz.scopes import Scope
from packages.connections.reference import contains_credential_value
from packages.connectors.notion_collab import (
    READ_PAGE_FIELDS,
    TOOL_SCHEMAS,
    NotionCollabConnector,
    allowlist_fields,
    personal_connection,
)
from packages.notion.http import HttpResponse
from packages.notion.models import NotionConfig, NotionTokens
from packages.notion.client import NotionClient
from packages.notion.tokens import TokenStore
from packages.tracing.context import RequestContext


class MockTransport:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.queue: list[HttpResponse] = []

    def push(self, status: int, body: dict[str, Any]) -> None:
        self.queue.append(HttpResponse(status=status, body=body, text=json.dumps(body)))

    def request(self, method: str, url: str, **kwargs: Any) -> HttpResponse:
        self.calls.append(
            {
                "method": method,
                "url": url,
                "json_body": kwargs.get("json_body"),
                "authorization": (kwargs.get("headers") or {}).get("Authorization", ""),
            }
        )
        if not self.queue:
            return HttpResponse(status=500, body={"code": "empty_queue"})
        return self.queue.pop(0)


def _ctx() -> RequestContext:
    return RequestContext(
        trace_id="trc_notion",
        request_id="req_notion",
        principal_id="employee-a",
        profile_id="employee-a",
        memberships=["all-employees"],
        release_id="scaffold",
        purpose="notion-collab-test",
    )


def _bare_connector() -> NotionCollabConnector:
    return NotionCollabConnector(
        store=TokenStore("/tmp/notion-collab-missing.json"),
        config=NotionConfig(),
    )


def _live_connector(tmp_path: Path, http: MockTransport) -> NotionCollabConnector:
    store = TokenStore(tmp_path / "tokens.json")
    store.save(
        NotionTokens.from_oauth_payload(
            {
                "access_token": "ntn_COLLABACCESS",
                "refresh_token": "nrt_COLLABREFRESH",
                "workspace_id": "ws_1",
                "workspace_name": "Example Workspace",
                "bot_id": "bot_1",
                "owner": {"type": "user", "user": {"id": "u1", "name": "<employee>"}},
            }
        )
    )
    config = NotionConfig(
        client_id="cid",
        client_secret="csecret",
        redirect_uri="http://127.0.0.1:8080/auth/notion/callback",
    )
    client = NotionClient(store, config, transport=http)
    return NotionCollabConnector(store=store, config=config, client=client)


def setup_function() -> None:
    reset_store()


def test_tools_require_request_context():
    connector = _bare_connector()
    with pytest.raises(ValueError, match="RequestContext"):
        connector.invoke(Scope.NOTION_READ_PAGE, None, {"page_id": "pg"})  # type: ignore[arg-type]


def test_read_is_not_configured_without_token():
    result = _bare_connector().invoke(Scope.NOTION_READ_PAGE, _ctx(), {"page_id": "pg_1"})
    assert result.status == "not_configured"
    assert result.configured is False
    assert "ntn_" not in json.dumps(result.model_dump())


def test_unknown_action_denied():
    result = _bare_connector().invoke("notion.delete_workspace", _ctx(), {})
    assert result.status == "deny"
    assert result.detail == "unknown_capability"


def test_field_allowlist_drops_secrets():
    raw = {
        "id": "pg_1",
        "title": "Notes",
        "url": "https://www.notion.so/pg_1",
        "parent_id": "db_1",
        "last_edited_time": "2026-01-01T00:00:00Z",
        "blocks": [],
        "plain_text": "hello",
        "token": "drop",
        "access_token": "ntn_SHOULD_DROP",
    }
    filtered = allowlist_fields(raw, READ_PAGE_FIELDS)
    assert set(filtered) == set(READ_PAGE_FIELDS)
    assert "token" not in filtered
    assert "access_token" not in filtered


def test_read_page_allowlists_and_hides_token(tmp_path: Path):
    http = MockTransport()
    http.push(
        200,
        {
            "object": "page",
            "id": "pg_1",
            "url": "https://www.notion.so/pg_1",
            "last_edited_time": "2026-01-01T00:00:00Z",
            "parent": {"type": "page_id", "page_id": "parent_1"},
            "properties": {
                "title": {"type": "title", "title": [{"plain_text": "Notes", "text": {"content": "Notes"}}]}
            },
        },
    )
    http.push(
        200,
        {
            "results": [
                {
                    "id": "b1",
                    "type": "paragraph",
                    "has_children": False,
                    "paragraph": {"rich_text": [{"plain_text": "Hello"}]},
                },
                {
                    "id": "b2",
                    "type": "unsupported",
                    "unsupported": {"block_type": "button"},
                    "has_children": False,
                },
            ],
            "has_more": False,
        },
    )
    result = _live_connector(tmp_path, http).invoke(
        Scope.NOTION_READ_PAGE, _ctx(), {"page_id": "pg_1", "token": "nope"}
    )
    assert result.status == "ok"
    assert result.payload["title"] == "Notes"
    assert result.payload["blocks"][1]["type"] == "unsupported"
    dumped = json.dumps(result.model_dump())
    assert "ntn_COLLABACCESS" not in dumped
    assert "nrt_COLLABREFRESH" not in dumped
    assert contains_credential_value(result.payload) is False


def test_write_without_approval_returns_preview():
    result = _bare_connector().invoke(
        Scope.NOTION_APPEND_BLOCKS,
        _ctx(),
        {"page_id": "pg_1", "blocks": [{"type": "paragraph", "paragraph": {"rich_text": []}}]},
    )
    assert result.status == "preview_required"
    assert result.payload["external_write"] is True
    assert result.payload["params_fingerprint"].startswith("sha256:")


def test_write_apply_requires_matching_approval(tmp_path: Path):
    ctx = _ctx()
    connector = _bare_connector()
    params = {
        "page_id": "pg_9",
        "blocks": [{"object": "block", "type": "paragraph", "paragraph": {"rich_text": []}}],
    }
    draft = connector.preview_write(Scope.NOTION_APPEND_BLOCKS, ctx, params)
    with pytest.raises(PermissionError, match="approval"):
        connector.apply_write(draft, ctx, params)


def test_preview_approval_apply_records_attribution(tmp_path: Path):
    ctx = _ctx()
    http = MockTransport()
    http.push(200, {"object": "list", "results": []})
    connector = _live_connector(tmp_path, http)
    params = {
        "page_id": "pg_9",
        "blocks": [{"object": "block", "type": "paragraph", "paragraph": {"rich_text": []}}],
    }
    draft = connector.preview_write(Scope.NOTION_APPEND_BLOCKS, ctx, params)
    req = create_request(
        ctx,
        Scope.NOTION_APPEND_BLOCKS,
        params,
        named_approvers=("employee-b",),
        preview_hash=draft.params_fingerprint,
        connection=personal_connection(ctx.principal_id),
    )
    resolve(req.approval_id, "employee-b", "approved")
    applied, payload = connector.apply_write(
        draft, ctx, params, approval_id=req.approval_id
    )
    assert applied.status == "recorded"
    assert applied.attribution["requested_by"] == "employee-a"
    assert applied.attribution["executed_as"] == "employee-a"
    assert applied.attribution["connection"] == "user:employee-a/notion-oauth"
    assert applied.attribution["approval"] == req.approval_id
    assert payload["page_id"] == "pg_9"
    assert payload["appended"] == 1
    dumped = json.dumps(applied.model_dump())
    assert "ntn_COLLABACCESS" not in dumped


def test_invoke_write_with_approval_ok(tmp_path: Path):
    ctx = _ctx()
    http = MockTransport()
    http.push(
        200,
        {
            "object": "page",
            "id": "pg_new",
            "url": "https://www.notion.so/pg_new",
            "properties": {
                "title": {"type": "title", "title": [{"plain_text": "New", "text": {"content": "New"}}]}
            },
        },
    )
    connector = _live_connector(tmp_path, http)
    params = {"parent_id": "pg_parent", "parent_type": "page_id", "title": "New"}
    draft = connector.preview_write(Scope.NOTION_CREATE_PAGE, ctx, params)
    req = create_request(
        ctx,
        Scope.NOTION_CREATE_PAGE,
        params,
        named_approvers=("employee-b",),
        preview_hash=draft.params_fingerprint,
        connection=personal_connection(ctx.principal_id),
    )
    resolve(req.approval_id, "employee-b", "approved")
    result = connector.invoke(
        Scope.NOTION_CREATE_PAGE,
        ctx,
        params,
        preview_obj=draft,
        approval_id=req.approval_id,
    )
    assert result.status == "ok"
    assert result.payload["result"]["id"] == "pg_new"
    assert result.payload["attribution"]["requested_by"] == "employee-a"


def test_connector_object_has_no_token_attrs(tmp_path: Path):
    connector = _live_connector(tmp_path, MockTransport())
    assert not hasattr(connector, "token")
    assert not hasattr(connector, "access_token")
    dumped = connector.__dict__
    assert contains_credential_value({k: v for k, v in dumped.items() if k != "_client"}) is False
    for name in TOOL_SCHEMAS:
        assert name.startswith("notion.")
