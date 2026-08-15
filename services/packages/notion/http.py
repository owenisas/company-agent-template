"""Injectable HTTP transport for Notion REST. Never logs Authorization."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

log = logging.getLogger("packages.notion.http")


def redact(value: str) -> str:
    """Strip token-like substrings from strings that may be logged."""
    if not value:
        return value
    lowered = value.lower()
    if "bearer " in lowered or "ntn_" in value or "nrt_" in value or "secret_" in lowered:
        return "<redacted>"
    return value


@dataclass
class HttpResponse:
    status: int
    headers: dict[str, str] = field(default_factory=dict)
    body: Any = None
    text: str = ""


class HttpTransport(Protocol):
    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
        basic_auth: tuple[str, str] | None = None,
        timeout: float = 30.0,
    ) -> HttpResponse: ...


class StdlibTransport:
    """urllib transport. Authorization header is never written to logs."""

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
        basic_auth: tuple[str, str] | None = None,
        timeout: float = 30.0,
    ) -> HttpResponse:
        import base64

        hdrs = dict(headers or {})
        data = None
        if json_body is not None:
            data = json.dumps(json_body).encode("utf-8")
            hdrs.setdefault("Content-Type", "application/json")
        if basic_auth is not None:
            raw = f"{basic_auth[0]}:{basic_auth[1]}".encode("utf-8")
            hdrs["Authorization"] = "Basic " + base64.b64encode(raw).decode("ascii")
        req = Request(url, data=data, headers=hdrs, method=method.upper())
        try:
            with urlopen(req, timeout=timeout) as resp:  # noqa: S310 — https only, caller-controlled
                text = resp.read().decode("utf-8")
                body: Any = None
                if text:
                    try:
                        body = json.loads(text)
                    except json.JSONDecodeError:
                        body = None
                return HttpResponse(
                    status=int(resp.status),
                    headers={k.lower(): v for k, v in resp.headers.items()},
                    body=body,
                    text=text,
                )
        except HTTPError as exc:
            text = exc.read().decode("utf-8", errors="replace")
            body = None
            if text:
                try:
                    body = json.loads(text)
                except json.JSONDecodeError:
                    body = None
            return HttpResponse(
                status=int(exc.code),
                headers={k.lower(): v for k, v in (exc.headers.items() if exc.headers else [])},
                body=body,
                text=text,
            )
        except URLError as exc:
            log.warning("notion transport error: %s", type(exc).__name__)
            return HttpResponse(status=0, body={"error": "transport_error"}, text="")
