"""Notion public-connection OAuth (authorization code + refresh rotation).

Authorize URL: https://api.notion.com/v1/oauth/authorize
Token URL:     POST https://api.notion.com/v1/oauth/token
Auth:          HTTP Basic client_id:client_secret

Refresh rotates both access and refresh tokens. The write is file-locked
so two processes cannot burn the same refresh token.
"""

from __future__ import annotations

import secrets
from typing import Any
from urllib.parse import urlencode

from packages.notion.http import HttpTransport, StdlibTransport
from packages.notion.models import NotionConfig, NotionTokens
from packages.notion.tokens import TokenStore, rotation_lock

AUTHORIZE_URL = "https://api.notion.com/v1/oauth/authorize"
TOKEN_URL = "https://api.notion.com/v1/oauth/token"
NOTION_VERSION = "2026-03-11"


class OAuthError(RuntimeError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(detail or code)
        self.code = code
        self.detail = detail


def new_oauth_state() -> str:
    return secrets.token_urlsafe(32)


def authorization_url(
    config: NotionConfig,
    state: str,
    *,
    owner: str = "user",
) -> str:
    if not config.client_id or not config.redirect_uri:
        raise OAuthError("not_configured", "NOTION_CLIENT_ID / NOTION_REDIRECT_URI missing")
    query = urlencode(
        {
            "owner": owner,
            "client_id": config.client_id,
            "redirect_uri": config.redirect_uri,
            "response_type": "code",
            "state": state,
        }
    )
    return f"{AUTHORIZE_URL}?{query}"


def _token_headers() -> dict[str, str]:
    return {
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _post_token(
    transport: HttpTransport,
    config: NotionConfig,
    body: dict[str, Any],
) -> NotionTokens:
    if not config.configured:
        raise OAuthError("not_configured", "Notion public connection credentials missing")
    response = transport.request(
        "POST",
        TOKEN_URL,
        headers=_token_headers(),
        json_body=body,
        basic_auth=(config.client_id, config.client_secret),
    )
    payload = response.body if isinstance(response.body, dict) else {}
    if response.status != 200 or not payload.get("access_token"):
        err = str(payload.get("error") or "token_exchange_failed")
        raise OAuthError(err, "oauth token request failed")
    return NotionTokens.from_oauth_payload(payload)


def exchange_code(
    config: NotionConfig,
    code: str,
    *,
    store: TokenStore,
    transport: HttpTransport | None = None,
) -> NotionTokens:
    if not code:
        raise OAuthError("invalid_request", "missing authorization code")
    http = transport or StdlibTransport()
    tokens = _post_token(
        http,
        config,
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": config.redirect_uri,
        },
    )
    store.save_locked(tokens)
    return tokens


def refresh_tokens(
    config: NotionConfig,
    store: TokenStore,
    *,
    transport: HttpTransport | None = None,
) -> NotionTokens:
    """Rotate access + refresh tokens under the store file lock."""
    http = transport or StdlibTransport()
    with rotation_lock(store.path):
        current = store.load()
        if current is None or not current.refresh_token:
            raise OAuthError("not_configured", "no refresh token stored")
        tokens = _post_token(
            http,
            config,
            {
                "grant_type": "refresh_token",
                "refresh_token": current.refresh_token,
            },
        )
        store.save(tokens)
        return tokens


def revoke_locally(store: TokenStore) -> None:
    """Drop the stored grant. User can also revoke in Notion Settings → Connections."""
    store.clear_locked()
