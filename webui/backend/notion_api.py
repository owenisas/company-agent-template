"""Notion OAuth connect API for the platform webui.

Tokens stay on the server. JSON responses never include access or refresh
tokens. These routes are also the surface a Hermes dashboard can call.
"""

from __future__ import annotations

import hmac
import os
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse

_SERVICES = Path(__file__).resolve().parents[2] / "services"
if str(_SERVICES) not in sys.path:
    sys.path.insert(0, str(_SERVICES))

from packages.notion.config import load_notion_config  # noqa: E402
from packages.notion.models import NotionConfig  # noqa: E402
from packages.notion.oauth import (  # noqa: E402
    OAuthError,
    authorization_url,
    exchange_code,
    new_oauth_state,
    revoke_locally,
)
from packages.notion.tokens import TokenStore  # noqa: E402

STATE_COOKIE = "notion_oauth_state"
STATE_MAX_AGE = 600

router = APIRouter(tags=["notion"])


def _config() -> NotionConfig:
    env_file = os.environ.get("NOTION_ENV_FILE") or os.environ.get("WEBUI_ENV_FILE")
    return load_notion_config(file_path=env_file)


def _store(config: NotionConfig) -> TokenStore:
    return TokenStore(config.token_path or None)


def public_status() -> dict[str, Any]:
    config = _config()
    store = _store(config)
    status = store.status()
    body = status.public_dict()
    body["configured"] = config.configured
    if not config.configured:
        body["detail"] = "oauth_app_not_configured"
    elif not status.connected:
        body["detail"] = "not_connected"
    return body


def _set_state_cookie(response: RedirectResponse | JSONResponse, state: str) -> None:
    secure = os.environ.get("WEBUI_SECURE_COOKIE", "").strip().lower() in {"1", "true", "yes"}
    response.set_cookie(
        key=STATE_COOKIE,
        value=state,
        max_age=STATE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/",
    )


def register_notion_routes(app, current_user) -> None:
    """Attach Notion routes onto the FastAPI app. `current_user` is the auth dependency."""

    @app.get("/api/notion/status")
    def notion_status(_user: dict = current_user) -> dict[str, Any]:
        return public_status()

    @app.get("/api/notion/connect")
    def notion_connect(request: Request, _user: dict = current_user) -> RedirectResponse:
        config = _config()
        if not config.configured:
            raise HTTPException(status_code=503, detail="Notion OAuth app is not configured")
        state = new_oauth_state()
        try:
            url = authorization_url(config, state)
        except OAuthError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        wants_json = "application/json" in request.headers.get("accept", "")
        if wants_json and request.query_params.get("redirect") == "0":
            response: RedirectResponse | JSONResponse = JSONResponse({"authorize_url": url})
        else:
            response = RedirectResponse(url=url, status_code=302)
        _set_state_cookie(response, state)
        return response  # type: ignore[return-value]

    @app.get("/auth/notion/callback")
    def notion_callback(
        request: Request,
        code: str | None = None,
        state: str | None = None,
        error: str | None = None,
    ) -> RedirectResponse:
        if error:
            return RedirectResponse(url=f"/?notion=denied&error={error}", status_code=303)
        cookie_state = request.cookies.get(STATE_COOKIE) or ""
        if not state or not cookie_state or not hmac.compare_digest(state, cookie_state):
            return RedirectResponse(url="/?notion=error&error=state_mismatch", status_code=303)
        if not code:
            return RedirectResponse(url="/?notion=error&error=missing_code", status_code=303)
        config = _config()
        store = _store(config)
        try:
            exchange_code(config, code, store=store)
        except OAuthError:
            return RedirectResponse(url="/?notion=error&error=exchange_failed", status_code=303)
        response = RedirectResponse(url="/?notion=connected", status_code=303)
        response.delete_cookie(STATE_COOKIE, path="/")
        return response

    @app.post("/api/notion/disconnect")
    def notion_disconnect(_user: dict = current_user) -> dict[str, Any]:
        config = _config()
        revoke_locally(_store(config))
        return {"ok": True, "connected": False}

    @app.delete("/api/notion")
    def notion_delete(_user: dict = current_user) -> dict[str, Any]:
        config = _config()
        revoke_locally(_store(config))
        return {"ok": True, "connected": False}

    # Silence unused import if a caller wants the router object.
    _ = urlencode
    _ = router
