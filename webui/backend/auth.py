"""Signed session cookies. Stdlib HMAC — no extra signing dependency."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from .config import COOKIE_MAX_AGE, secret_key


class AuthError(Exception):
    pass


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


def _sign(payload: str) -> str:
    digest = hmac.new(
        secret_key().encode("utf-8"),
        payload.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return _b64encode(digest)


def issue_session(username: str, max_age: int = COOKIE_MAX_AGE) -> str:
    body = {
        "u": username,
        "exp": int(time.time()) + max_age,
        "v": 1,
    }
    payload = _b64encode(json.dumps(body, separators=(",", ":")).encode("utf-8"))
    return f"v1.{payload}.{_sign(payload)}"


def read_session(token: str | None) -> str:
    if not token:
        raise AuthError("not signed in")
    parts = token.split(".")
    if len(parts) != 3 or parts[0] != "v1":
        raise AuthError("invalid session")
    _, payload, signature = parts
    expected = _sign(payload)
    if not hmac.compare_digest(signature, expected):
        raise AuthError("invalid session")
    try:
        body: dict[str, Any] = json.loads(_b64decode(payload))
    except (ValueError, json.JSONDecodeError) as exc:
        raise AuthError("invalid session") from exc
    if int(body.get("exp") or 0) < int(time.time()):
        raise AuthError("session expired")
    username = (body.get("u") or "").strip()
    if not username:
        raise AuthError("invalid session")
    return username
