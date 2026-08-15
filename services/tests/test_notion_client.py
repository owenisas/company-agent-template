"""Offline Notion REST client tests. Mock HTTP only."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from packages.notion.client import NOTION_VERSION, NotionAPIError, NotionClient, summarize_block
from packages.notion.http import HttpResponse
from packages.notion.models import NotionConfig, NotionTokens
from packages.notion.tokens import TokenStore


class MockTransport:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.queue: list[HttpResponse] = []

    def push(self, status: int, body: dict[str, Any], headers: dict[str, str] | None = None) -> None:
        self.queue.append(
            HttpResponse(
                status=status,
                body=body,
                headers=headers or {},
                text=json.dumps(body),
            )
        )

    def request(self, method: str, url: str, **kwargs: Any) -> HttpResponse:
        headers = dict(kwargs.get("headers") or {})
        self.calls.append(
            {
                "method": method,
                "url": url,
                "json_body": kwargs.get("json_body"),
                "header_names": sorted(k.lower() for k in headers),
                "authorization": headers.get("Authorization", ""),
                "notion_version": headers.get("Notion-Version"),
            }
        )
        if not self.queue:
            return HttpResponse(status=500, body={"code": "empty_queue"})
        return self.queue.pop(0)


def _client(tmp_path: Path, http: MockTransport) -> NotionClient:
    store = TokenStore(tmp_path / "tokens.json")
    store.save(
        NotionTokens.from_oauth_payload(
            {
                "access_token": "ntn_CLIENTACCESS",
                "refresh_token": "nrt_CLIENTREFRESH",
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
    return NotionClient(store, config, transport=http)


def test_request_sets_version_and_bearer(tmp_path: Path):
    http = MockTransport()
    http.push(200, {"object": "page", "id": "pg_1", "properties": {}})
    client = _client(tmp_path, http)
    client.get_page("pg_1")
    call = http.calls[0]
    assert call["method"] == "GET"
    assert call["url"].endswith("/pages/pg_1")
    assert call["notion_version"] == NOTION_VERSION == "2026-03-11"
    assert call["authorization"].startswith("Bearer ")
    assert "authorization" in call["header_names"]


def test_pagination_follows_cursor(tmp_path: Path):
    http = MockTransport()
    http.push(
        200,
        {
            "results": [{"id": "b1", "type": "paragraph", "paragraph": {"rich_text": []}}],
            "has_more": True,
            "next_cursor": "cur_2",
        },
    )
    http.push(
        200,
        {
            "results": [{"id": "b2", "type": "paragraph", "paragraph": {"rich_text": []}}],
            "has_more": False,
        },
    )
    client = _client(tmp_path, http)
    blocks = client.list_block_children("pg_1")
    assert [b["id"] for b in blocks] == ["b1", "b2"]
    assert "start_cursor=cur_2" in http.calls[1]["url"]
    assert http.calls[0]["json_body"] is None


def test_unsupported_block_is_tolerated():
    summary = summarize_block(
        {
            "id": "blk_x",
            "type": "unsupported",
            "unsupported": {"block_type": "form"},
            "has_children": False,
        }
    )
    assert summary["type"] == "unsupported"
    assert summary["block_type"] == "form"
    assert "form_fields" not in summary


def test_401_refreshes_and_retries_once(tmp_path: Path):
    http = MockTransport()
    http.push(401, {"code": "unauthorized"})
    http.push(
        200,
        {
            "access_token": "ntn_ROTATED",
            "refresh_token": "nrt_ROTATED",
            "workspace_id": "ws_1",
            "workspace_name": "Example Workspace",
            "bot_id": "bot_1",
            "owner": {"type": "user", "user": {"id": "u1", "name": "<employee>"}},
        },
    )
    http.push(200, {"object": "page", "id": "pg_1", "properties": {}})
    client = _client(tmp_path, http)
    page = client.get_page("pg_1")
    assert page["id"] == "pg_1"
    assert len(http.calls) == 3
    assert http.calls[1]["url"].endswith("/oauth/token")


def test_errors_do_not_include_token(tmp_path: Path):
    http = MockTransport()
    http.push(400, {"code": "validation_error", "message": "bad"})
    client = _client(tmp_path, http)
    with pytest.raises(NotionAPIError) as exc:
        client.get_page("pg_missing")
    text = str(exc.value)
    assert "ntn_CLIENTACCESS" not in text
    assert "nrt_CLIENTREFRESH" not in text


def test_search_and_query_build_expected_paths(tmp_path: Path):
    http = MockTransport()
    http.push(200, {"results": [], "has_more": False})
    http.push(200, {"results": [], "has_more": False})
    client = _client(tmp_path, http)
    client.search("handbook")
    client.query_database("ds_1")
    assert http.calls[0]["url"].endswith("/search")
    assert http.calls[0]["json_body"]["query"] == "handbook"
    assert "/data_sources/ds_1/query" in http.calls[1]["url"]
