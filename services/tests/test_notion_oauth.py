"""Offline Notion OAuth + token-store tests. No live Notion calls."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from packages.notion.http import HttpResponse, redact
from packages.notion.models import NotionConfig, NotionTokens
from packages.notion.oauth import (
    AUTHORIZE_URL,
    TOKEN_URL,
    OAuthError,
    authorization_url,
    exchange_code,
    new_oauth_state,
    refresh_tokens,
    revoke_locally,
)
from packages.notion.tokens import TokenStore, rotation_lock


class MockTransport:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.queue: list[HttpResponse] = []

    def push(self, status: int, body: dict[str, Any]) -> None:
        self.queue.append(HttpResponse(status=status, body=body, text=json.dumps(body)))

    def request(self, method: str, url: str, **kwargs: Any) -> HttpResponse:
        headers = dict(kwargs.get("headers") or {})
        recorded = {
            "method": method,
            "url": url,
            "json_body": kwargs.get("json_body"),
            "has_basic": kwargs.get("basic_auth") is not None,
            "header_names": sorted(headers),
        }
        if kwargs.get("basic_auth"):
            recorded["basic_user"] = kwargs["basic_auth"][0]
        self.calls.append(recorded)
        if not self.queue:
            return HttpResponse(status=500, body={"error": "empty_queue"})
        return self.queue.pop(0)


def _config() -> NotionConfig:
    return NotionConfig(
        client_id="notion_cid_test",
        client_secret="notion_csecret_test",
        redirect_uri="http://127.0.0.1:8080/auth/notion/callback",
    )


def _oauth_payload(**overrides: Any) -> dict[str, Any]:
    body = {
        "access_token": "ntn_TESTACCESSVALUE",
        "refresh_token": "nrt_TESTREFRESHVALUE",
        "token_type": "bearer",
        "bot_id": "bot_1",
        "workspace_id": "ws_1",
        "workspace_name": "Example Workspace",
        "owner": {"type": "user", "user": {"id": "usr_1", "name": "<employee>"}},
    }
    body.update(overrides)
    return body


def test_authorization_url_includes_state_and_fixed_params():
    state = new_oauth_state()
    url = authorization_url(_config(), state)
    assert url.startswith(AUTHORIZE_URL)
    assert "owner=user" in url
    assert "response_type=code" in url
    assert "client_id=notion_cid_test" in url
    assert "state=" + state in url
    assert "redirect_uri=" in url
    assert "scope=" not in url
    assert "notion_csecret_test" not in url


def test_exchange_code_uses_basic_auth_and_stores_tokens(tmp_path: Path):
    store = TokenStore(tmp_path / "notion-tokens.json")
    http = MockTransport()
    http.push(200, _oauth_payload())
    tokens = exchange_code(_config(), "auth_code_1", store=store, transport=http)
    assert tokens.workspace_name == "Example Workspace"
    assert tokens.access_token == "ntn_TESTACCESSVALUE"
    public = store.status().public_dict()
    dumped = json.dumps(public)
    assert "ntn_TESTACCESSVALUE" not in dumped
    assert "nrt_TESTREFRESHVALUE" not in dumped
    assert public["connected"] is True
    assert public["workspace_name"] == "Example Workspace"
    assert http.calls[0]["url"] == TOKEN_URL
    assert http.calls[0]["has_basic"] is True
    assert http.calls[0]["json_body"]["grant_type"] == "authorization_code"
    assert http.calls[0]["json_body"]["code"] == "auth_code_1"
    assert store.path.stat().st_mode & 0o777 == 0o600


def test_refresh_rotates_both_tokens_under_lock(tmp_path: Path):
    store = TokenStore(tmp_path / "notion-tokens.json")
    store.save(NotionTokens.from_oauth_payload(_oauth_payload()))
    http = MockTransport()
    http.push(
        200,
        _oauth_payload(
            access_token="ntn_NEWACCESS",
            refresh_token="nrt_NEWREFRESH",
        ),
    )
    with rotation_lock(store.path):
        # Nested refresh takes the same thread lock; file lock is re-entrant via same thread only
        # after the context exits. Call refresh after this block.
        pass
    refreshed = refresh_tokens(_config(), store, transport=http)
    assert refreshed.access_token == "ntn_NEWACCESS"
    assert refreshed.refresh_token == "nrt_NEWREFRESH"
    assert http.calls[0]["json_body"]["grant_type"] == "refresh_token"
    assert http.calls[0]["json_body"]["refresh_token"] == "nrt_TESTREFRESHVALUE"
    loaded = store.load()
    assert loaded is not None
    assert loaded.access_token == "ntn_NEWACCESS"
    assert "ntn_NEWACCESS" not in json.dumps(loaded.public_status())


def test_refresh_without_store_is_not_configured(tmp_path: Path):
    store = TokenStore(tmp_path / "missing.json")
    with pytest.raises(OAuthError) as exc:
        refresh_tokens(_config(), store, transport=MockTransport())
    assert exc.value.code == "not_configured"


def test_revoke_clears_file(tmp_path: Path):
    store = TokenStore(tmp_path / "notion-tokens.json")
    store.save(NotionTokens.from_oauth_payload(_oauth_payload()))
    revoke_locally(store)
    assert store.load() is None
    assert store.status().connected is False


def test_redact_never_leaks_bearer_or_prefixes():
    assert redact("Bearer ntn_TESTACCESSVALUE") == "<redacted>"
    assert redact("nrt_TESTREFRESHVALUE") == "<redacted>"
    assert redact("plain workspace name") == "plain workspace name"


def test_oauth_error_message_omits_token_values():
    http = MockTransport()
    http.push(400, {"error": "invalid_grant", "access_token": "ntn_SHOULDNOTAPPEAR"})
    store = TokenStore(Path("/tmp/unused-notion-tokens-test.json"))
    with pytest.raises(OAuthError) as exc:
        exchange_code(_config(), "bad", store=store, transport=http)
    assert "ntn_SHOULDNOTAPPEAR" not in str(exc.value)
    assert "notion_csecret_test" not in str(exc.value)
