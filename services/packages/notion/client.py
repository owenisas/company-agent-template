"""Thin Notion REST client.

Headers: Authorization Bearer <server token>, Notion-Version, Content-Type.
Pagination follows start_cursor / has_more.
Unsupported blocks are tolerated (type kept, no crash).
401 retries once after a locked refresh.
Token values never appear in exceptions or public results.
"""

from __future__ import annotations

from typing import Any, Callable
from urllib.parse import urlencode

from packages.notion.http import HttpResponse, HttpTransport, StdlibTransport
from packages.notion.models import NotionConfig, NotionTokens
from packages.notion.oauth import NOTION_VERSION, OAuthError, refresh_tokens
from packages.notion.tokens import TokenStore

API_BASE = "https://api.notion.com/v1"
PAGE_SIZE_MAX = 100

# Re-export for callers that import version from the client.
__all__ = ["API_BASE", "NOTION_VERSION", "NotionAPIError", "NotionClient"]


class NotionAPIError(RuntimeError):
    def __init__(self, status: int, code: str, detail: str = "") -> None:
        super().__init__(detail or code)
        self.status = status
        self.code = code
        self.detail = detail


def _title_from_properties(properties: dict[str, Any] | None) -> str:
    if not isinstance(properties, dict):
        return ""
    for value in properties.values():
        if not isinstance(value, dict):
            continue
        if value.get("type") != "title" and "title" not in value:
            continue
        chunks = value.get("title") or []
        parts: list[str] = []
        for chunk in chunks:
            if isinstance(chunk, dict):
                plain = chunk.get("plain_text")
                if plain:
                    parts.append(str(plain))
                else:
                    text = chunk.get("text") or {}
                    if isinstance(text, dict) and text.get("content"):
                        parts.append(str(text["content"]))
        if parts:
            return "".join(parts)
    return ""


def _plain_from_rich_text(rich: Any) -> str:
    if not isinstance(rich, list):
        return ""
    parts: list[str] = []
    for chunk in rich:
        if isinstance(chunk, dict):
            parts.append(str(chunk.get("plain_text") or ""))
    return "".join(parts)


def summarize_block(block: dict[str, Any]) -> dict[str, Any]:
    """Allowlisted block view. Unsupported types do not raise."""
    block_type = str(block.get("type") or "unsupported")
    payload = block.get(block_type) if isinstance(block.get(block_type), dict) else {}
    summary: dict[str, Any] = {
        "id": block.get("id"),
        "type": block_type,
        "has_children": bool(block.get("has_children")),
    }
    if block_type == "unsupported":
        summary["block_type"] = (payload or {}).get("block_type") or block.get("block_type")
        return summary
    if isinstance(payload, dict):
        if "rich_text" in payload:
            summary["text"] = _plain_from_rich_text(payload.get("rich_text"))
        if payload.get("checked") is not None:
            summary["checked"] = payload.get("checked")
        if payload.get("language"):
            summary["language"] = payload.get("language")
        if payload.get("icon"):
            summary["icon"] = payload.get("icon")
        if payload.get("url"):
            summary["url"] = payload.get("url")
    return summary


def summarize_page(page: dict[str, Any]) -> dict[str, Any]:
    props = page.get("properties") if isinstance(page.get("properties"), dict) else {}
    return {
        "id": page.get("id"),
        "object": page.get("object"),
        "title": _title_from_properties(props) or page.get("title") or "",
        "url": page.get("url"),
        "parent_id": _parent_id(page.get("parent")),
        "last_edited_time": page.get("last_edited_time"),
        "archived": bool(page.get("archived")),
    }


def _parent_id(parent: Any) -> str | None:
    if not isinstance(parent, dict):
        return None
    for key in ("page_id", "database_id", "data_source_id", "block_id"):
        if parent.get(key):
            return str(parent[key])
    return None


def allowlist_row_properties(properties: dict[str, Any] | None) -> dict[str, Any]:
    """Keep typed scalar-ish property values; drop unknown blobs."""
    if not isinstance(properties, dict):
        return {}
    allowed_types = {
        "title",
        "rich_text",
        "number",
        "select",
        "multi_select",
        "status",
        "date",
        "checkbox",
        "url",
        "email",
        "phone_number",
        "created_time",
        "last_edited_time",
    }
    out: dict[str, Any] = {}
    for name, raw in properties.items():
        if not isinstance(raw, dict):
            continue
        kind = str(raw.get("type") or "")
        if kind not in allowed_types:
            out[name] = {"type": kind or "unsupported"}
            continue
        value = raw.get(kind)
        if kind == "title":
            out[name] = {"type": kind, "value": _title_from_properties({name: raw})}
        elif kind == "rich_text":
            out[name] = {"type": kind, "value": _plain_from_rich_text(value)}
        elif kind == "select" and isinstance(value, dict):
            out[name] = {"type": kind, "value": value.get("name")}
        elif kind == "status" and isinstance(value, dict):
            out[name] = {"type": kind, "value": value.get("name")}
        elif kind == "multi_select" and isinstance(value, list):
            out[name] = {
                "type": kind,
                "value": [v.get("name") for v in value if isinstance(v, dict)],
            }
        elif kind == "date" and isinstance(value, dict):
            out[name] = {"type": kind, "value": value.get("start"), "end": value.get("end")}
        else:
            out[name] = {"type": kind, "value": value}
    return out


class NotionClient:
    """Server-side REST wrapper. Construct with a TokenStore, never a raw token."""

    def __init__(
        self,
        store: TokenStore,
        config: NotionConfig,
        *,
        transport: HttpTransport | None = None,
        refresher: Callable[[], NotionTokens] | None = None,
    ) -> None:
        self.store = store
        self.config = config
        self.transport = transport or StdlibTransport()
        self._refresher = refresher

    def configured(self) -> bool:
        tokens = self.store.load()
        return bool(tokens and tokens.has_access_token())

    def _tokens(self) -> NotionTokens:
        tokens = self.store.load()
        if tokens is None or not tokens.has_access_token():
            raise NotionAPIError(401, "not_configured", "no Notion access token")
        return tokens

    def _headers(self, tokens: NotionTokens) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {tokens.access_token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        _retried: bool = False,
    ) -> dict[str, Any]:
        tokens = self._tokens()
        url = path if path.startswith("http") else f"{API_BASE}{path}"
        if params:
            query = urlencode({k: v for k, v in params.items() if v is not None})
            url = f"{url}{'&' if '?' in url else '?'}{query}"
        response = self.transport.request(
            method,
            url,
            headers=self._headers(tokens),
            json_body=json_body,
        )
        if response.status == 401 and not _retried:
            self._refresh()
            return self.request(
                method,
                path,
                json_body=json_body,
                params=params,
                _retried=True,
            )
        return self._parse(response)

    def _refresh(self) -> NotionTokens:
        if self._refresher is not None:
            return self._refresher()
        try:
            return refresh_tokens(self.config, self.store, transport=self.transport)
        except OAuthError as exc:
            raise NotionAPIError(401, exc.code, "token refresh failed") from exc

    def _parse(self, response: HttpResponse) -> dict[str, Any]:
        body = response.body if isinstance(response.body, dict) else {}
        if response.status >= 400 or response.status == 0:
            code = str(body.get("code") or body.get("error") or "notion_error")
            raise NotionAPIError(response.status, code, "notion request failed")
        return body

    def collect_pages(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        cursor: str | None = None
        remaining = max(1, limit)
        verb = method.upper()
        while remaining > 0:
            page_size = min(PAGE_SIZE_MAX, remaining)
            if verb == "GET":
                params: dict[str, Any] = {"page_size": page_size}
                if cursor:
                    params["start_cursor"] = cursor
                payload = self.request(verb, path, params=params)
            else:
                body = dict(json_body or {})
                body["page_size"] = page_size
                if cursor:
                    body["start_cursor"] = cursor
                payload = self.request(verb, path, json_body=body)
            batch = payload.get("results") or []
            if isinstance(batch, list):
                items.extend(item for item in batch if isinstance(item, dict))
            if not payload.get("has_more"):
                break
            cursor = payload.get("next_cursor")
            if not cursor:
                break
            remaining = limit - len(items)
        return items

    def get_page(self, page_id: str) -> dict[str, Any]:
        return self.request("GET", f"/pages/{page_id}")

    def list_block_children(self, block_id: str, *, limit: int = 200) -> list[dict[str, Any]]:
        return self.collect_pages("GET", f"/blocks/{block_id}/children", limit=limit)

    def search(self, query: str, *, limit: int = 20, filter_object: str | None = None) -> list[dict[str, Any]]:
        body: dict[str, Any] = {"query": query}
        if filter_object:
            body["filter"] = {"value": filter_object, "property": "object"}
        return self.collect_pages("POST", "/search", json_body=body, limit=limit)

    def query_database(
        self,
        database_id: str,
        *,
        filter_obj: dict[str, Any] | None = None,
        sorts: list[dict[str, Any]] | None = None,
        limit: int = 50,
        use_data_source: bool = True,
    ) -> list[dict[str, Any]]:
        body: dict[str, Any] = {}
        if filter_obj:
            body["filter"] = filter_obj
        if sorts:
            body["sorts"] = sorts
        path = (
            f"/data_sources/{database_id}/query"
            if use_data_source
            else f"/databases/{database_id}/query"
        )
        try:
            return self.collect_pages("POST", path, json_body=body, limit=limit)
        except NotionAPIError as exc:
            if use_data_source and exc.status == 404:
                return self.query_database(
                    database_id,
                    filter_obj=filter_obj,
                    sorts=sorts,
                    limit=limit,
                    use_data_source=False,
                )
            raise

    def create_page(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.request("POST", "/pages", json_body=body)

    def append_blocks(self, block_id: str, children: list[dict[str, Any]]) -> dict[str, Any]:
        return self.request(
            "PATCH",
            f"/blocks/{block_id}/children",
            json_body={"children": children},
        )

    def update_page(self, page_id: str, properties: dict[str, Any]) -> dict[str, Any]:
        return self.request("PATCH", f"/pages/{page_id}", json_body={"properties": properties})

    def read_page(self, page_id: str, *, block_limit: int = 200) -> dict[str, Any]:
        page = self.get_page(page_id)
        summary = summarize_page(page)
        blocks = [summarize_block(b) for b in self.list_block_children(page_id, limit=block_limit)]
        summary["blocks"] = blocks
        summary["plain_text"] = "\n".join(
            str(b.get("text")) for b in blocks if b.get("text")
        )
        return summary
