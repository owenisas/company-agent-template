"""Human ↔ agent Notion collaboration connector.

Typed, field-allowlisted tools. Server-held OAuth token. Writes go through
preview → approval → apply (packages.actions.preview_apply + packages.approval)
and carry spec 30.2 attribution. Tokens never enter the result payload.
"""

from __future__ import annotations

from typing import Any

from packages.actions.preview_apply import ApplyResult, Preview, apply, preview
from packages.authz.scopes import Scope
from packages.connectors.base import Connector, ConnectorAction, ConnectorResult
from packages.notion.client import (
    NotionAPIError,
    NotionClient,
    allowlist_row_properties,
    summarize_page,
)
from packages.notion.config import load_notion_config
from packages.notion.models import NotionConfig
from packages.notion.tokens import TokenStore
from packages.tracing.attribution import attribution_from_parts
from packages.tracing.context import RequestContext

READ_PAGE_FIELDS: tuple[str, ...] = (
    "id",
    "title",
    "url",
    "parent_id",
    "last_edited_time",
    "blocks",
    "plain_text",
)
SEARCH_FIELDS: tuple[str, ...] = ("id", "title", "url", "object", "last_edited_time")
QUERY_ROW_FIELDS: tuple[str, ...] = ("id", "url", "title", "properties", "last_edited_time")
CREATE_PAGE_PARAMS: tuple[str, ...] = (
    "parent_id",
    "parent_type",
    "title",
    "properties",
    "children",
)
APPEND_BLOCKS_PARAMS: tuple[str, ...] = ("page_id", "blocks")
UPDATE_PROPERTY_PARAMS: tuple[str, ...] = (
    "page_id",
    "property_name",
    "property_type",
    "value",
)

READ_ACTIONS = frozenset(
    {Scope.NOTION_READ_PAGE, Scope.NOTION_SEARCH, Scope.NOTION_QUERY_DATABASE}
)
WRITE_ACTIONS = frozenset(
    {
        Scope.NOTION_CREATE_PAGE,
        Scope.NOTION_APPEND_BLOCKS,
        Scope.NOTION_UPDATE_PAGE_PROPERTY,
    }
)

NOTION_COLLAB_ACTIONS: tuple[ConnectorAction, ...] = (
    ConnectorAction(
        name=Scope.NOTION_READ_PAGE,
        risk_tier="R0",
        description="Read a Notion page title and allowlisted blocks.",
        preview_required=False,
    ),
    ConnectorAction(
        name=Scope.NOTION_SEARCH,
        risk_tier="R0",
        description="Search Notion pages and data sources by title.",
        preview_required=False,
    ),
    ConnectorAction(
        name=Scope.NOTION_QUERY_DATABASE,
        risk_tier="R0",
        description="Query an allowlisted Notion database / data source.",
        preview_required=False,
    ),
    ConnectorAction(
        name=Scope.NOTION_CREATE_PAGE,
        risk_tier="R2",
        description="Create a Notion page (preview + approval required).",
        preview_required=True,
    ),
    ConnectorAction(
        name=Scope.NOTION_APPEND_BLOCKS,
        risk_tier="R2",
        description="Append blocks to a Notion page (preview + approval required).",
        preview_required=True,
    ),
    ConnectorAction(
        name=Scope.NOTION_UPDATE_PAGE_PROPERTY,
        risk_tier="R2",
        description="Update one Notion page property (preview + approval required).",
        preview_required=True,
    ),
)

TOOL_SCHEMAS: dict[str, dict[str, tuple[str, ...]]] = {
    Scope.NOTION_READ_PAGE: {"params": ("page_id",), "fields": READ_PAGE_FIELDS},
    Scope.NOTION_SEARCH: {"params": ("query",), "fields": SEARCH_FIELDS},
    Scope.NOTION_QUERY_DATABASE: {
        "params": ("database_id",),
        "fields": QUERY_ROW_FIELDS,
    },
    Scope.NOTION_CREATE_PAGE: {"params": CREATE_PAGE_PARAMS, "fields": ("id", "url", "title")},
    Scope.NOTION_APPEND_BLOCKS: {
        "params": APPEND_BLOCKS_PARAMS,
        "fields": ("page_id", "appended"),
    },
    Scope.NOTION_UPDATE_PAGE_PROPERTY: {
        "params": UPDATE_PROPERTY_PARAMS,
        "fields": ("id", "url", "title"),
    },
}

CONNECTION_SHARED = Scope.CONN_NOTION_OAUTH
_NOT_CONFIGURED = "not_configured"


def allowlist_fields(payload: dict[str, Any], allowed: tuple[str, ...]) -> dict[str, Any]:
    return {key: payload[key] for key in allowed if key in payload}


def allowlist_params(params: dict[str, Any] | None, allowed: tuple[str, ...]) -> dict[str, Any]:
    raw = params or {}
    return {key: raw[key] for key in allowed if key in raw}


def personal_connection(principal_id: str) -> str:
    return f"user:{principal_id}/notion-oauth"


def _property_payload(property_type: str, value: Any) -> dict[str, Any]:
    if property_type == "title":
        return {"title": [{"text": {"content": str(value)}}]}
    if property_type == "rich_text":
        return {"rich_text": [{"text": {"content": str(value)}}]}
    if property_type == "select":
        return {"select": {"name": str(value)}}
    if property_type == "status":
        return {"status": {"name": str(value)}}
    if property_type == "multi_select":
        names = value if isinstance(value, list) else [value]
        return {"multi_select": [{"name": str(n)} for n in names]}
    if property_type == "checkbox":
        return {"checkbox": bool(value)}
    if property_type == "number":
        return {"number": value}
    if property_type == "url":
        return {"url": str(value)}
    if property_type == "email":
        return {"email": str(value)}
    if property_type == "date":
        if isinstance(value, dict):
            return {"date": value}
        return {"date": {"start": str(value)}}
    raise ValueError("unsupported_property_type")


def _create_page_body(params: dict[str, Any]) -> dict[str, Any]:
    parent_type = str(params.get("parent_type") or "page_id")
    parent_id = str(params["parent_id"])
    if parent_type in {"database_id", "data_source_id"}:
        parent = {parent_type: parent_id}
        properties = dict(params.get("properties") or {})
        if params.get("title") and "title" not in {k.lower() for k in properties}:
            # Common default title property name is Name.
            properties.setdefault(
                "Name",
                {"title": [{"text": {"content": str(params["title"])}}]},
            )
    else:
        parent = {"page_id": parent_id}
        properties = {
            "title": {"title": [{"text": {"content": str(params.get("title") or "Untitled")}}]}
        }
        extra = params.get("properties")
        if isinstance(extra, dict):
            properties.update(extra)
    body: dict[str, Any] = {"parent": parent, "properties": properties}
    children = params.get("children")
    if isinstance(children, list) and children:
        body["children"] = children
    return body


class NotionCollabConnector(Connector):
    """Collaboration tools. Credentials live in TokenStore, not on this object."""

    connection_id = CONNECTION_SHARED
    system = "notion"

    def __init__(
        self,
        *,
        store: TokenStore | None = None,
        config: NotionConfig | None = None,
        client: NotionClient | None = None,
    ) -> None:
        self._config = config if config is not None else load_notion_config()
        token_path = self._config.token_path or None
        self._store = store if store is not None else TokenStore(token_path)
        self._client = client

    def actions(self) -> list[ConnectorAction]:
        return list(NOTION_COLLAB_ACTIONS)

    @property
    def configured(self) -> bool:  # type: ignore[override]
        return self._store.load() is not None

    def _client_or_none(self) -> NotionClient | None:
        if self._client is not None:
            return self._client
        if self._store.load() is None:
            return None
        return NotionClient(self._store, self._config)

    def invoke(
        self,
        action: str,
        ctx: RequestContext,
        params: dict[str, Any] | None = None,
        *,
        preview_obj: Preview | None = None,
        approval_id: str | None = None,
    ) -> ConnectorResult:
        RequestContext.require(ctx)
        if action not in TOOL_SCHEMAS:
            return ConnectorResult(
                status="deny",
                configured=self.configured,
                action=action,
                detail="unknown_capability",
            )
        schema = TOOL_SCHEMAS[action]
        clean = allowlist_params(params, schema["params"])
        if action in WRITE_ACTIONS:
            extra = (params or {}).get("approval_id")
            approval = approval_id or (str(extra) if extra else None)
            return self._invoke_write(action, ctx, clean, preview_obj, approval)
        if not self.configured:
            return ConnectorResult(
                status="not_configured",
                configured=False,
                action=action,
                detail=_NOT_CONFIGURED,
                payload={"fields": list(schema["fields"])},
            )
        return self._invoke_read(action, ctx, clean)

    def preview_write(
        self,
        action: str,
        ctx: RequestContext,
        params: dict[str, Any] | None = None,
    ) -> Preview:
        RequestContext.require(ctx)
        if action not in WRITE_ACTIONS:
            raise PermissionError("unknown_capability")
        schema = TOOL_SCHEMAS[action]
        clean = allowlist_params(params, schema["params"])
        return preview(
            action,
            clean,
            ctx,
            connection=personal_connection(ctx.principal_id),
        )

    def apply_write(
        self,
        preview_obj: Preview,
        ctx: RequestContext,
        params: dict[str, Any],
        *,
        approval_id: str | None = None,
    ) -> tuple[ApplyResult, dict[str, Any]]:
        RequestContext.require(ctx)
        action = preview_obj.capability_id
        if action not in WRITE_ACTIONS:
            raise PermissionError("unknown_capability")
        schema = TOOL_SCHEMAS[action]
        clean = allowlist_params(params, schema["params"])
        connection = personal_connection(ctx.principal_id)
        applied = apply(
            preview_obj,
            ctx,
            capability_id=action,
            params=clean,
            approval_id=approval_id,
            executed_as=ctx.principal_id,
            connection=connection,
        )
        attribution_from_parts(
            requested_by=applied.attribution["requested_by"] or ctx.principal_id,
            agent_profile=applied.attribution["agent_profile"] or ctx.principal_id,
            executed_as=applied.attribution["executed_as"] or ctx.principal_id,
            connection=applied.attribution.get("connection"),
            approval=applied.attribution.get("approval"),
        )
        if not self.configured:
            return applied, {"status": "not_configured"}
        payload = self._execute_write(action, clean)
        return applied, payload

    def _invoke_write(
        self,
        action: str,
        ctx: RequestContext,
        clean: dict[str, Any],
        preview_obj: Preview | None,
        approval_id: str | None,
    ) -> ConnectorResult:
        if preview_obj is None or not approval_id:
            draft = preview_obj or preview(
                action,
                clean,
                ctx,
                connection=personal_connection(ctx.principal_id),
            )
            return ConnectorResult(
                status="preview_required",
                configured=self.configured,
                action=action,
                detail="preview_and_approval_required",
                payload={
                    "preview_id": draft.preview_id,
                    "effect_description": draft.effect_description,
                    "params_fingerprint": draft.params_fingerprint,
                    "risk_tier": draft.risk_tier,
                    "external_write": draft.external_write,
                },
            )
        try:
            applied, payload = self.apply_write(
                preview_obj, ctx, clean, approval_id=approval_id
            )
        except PermissionError as exc:
            return ConnectorResult(
                status="deny",
                configured=self.configured,
                action=action,
                detail=str(exc),
            )
        if payload.get("status") == "not_configured":
            return ConnectorResult(
                status="not_configured",
                configured=False,
                action=action,
                detail=_NOT_CONFIGURED,
                payload={"attribution": applied.attribution},
            )
        fields = TOOL_SCHEMAS[action]["fields"]
        return ConnectorResult(
            status="ok",
            configured=True,
            action=action,
            detail="applied",
            payload={
                "result": allowlist_fields(payload, fields),
                "attribution": applied.attribution,
                "approval_id": applied.approval_id,
                "preview_id": applied.preview_id,
            },
        )

    def _invoke_read(
        self,
        action: str,
        ctx: RequestContext,
        clean: dict[str, Any],
    ) -> ConnectorResult:
        _ = ctx
        client = self._client_or_none()
        if client is None:
            return ConnectorResult(
                status="not_configured",
                configured=False,
                action=action,
                detail=_NOT_CONFIGURED,
            )
        try:
            if action == Scope.NOTION_READ_PAGE:
                raw = client.read_page(str(clean["page_id"]))
                payload = allowlist_fields(raw, READ_PAGE_FIELDS)
            elif action == Scope.NOTION_SEARCH:
                hits = client.search(str(clean.get("query") or ""))
                payload = {
                    "results": [
                        allowlist_fields(summarize_page(hit), SEARCH_FIELDS) for hit in hits
                    ]
                }
            elif action == Scope.NOTION_QUERY_DATABASE:
                rows = client.query_database(str(clean["database_id"]))
                payload = {
                    "results": [
                        {
                            "id": row.get("id"),
                            "url": row.get("url"),
                            "title": summarize_page(row).get("title"),
                            "last_edited_time": row.get("last_edited_time"),
                            "properties": allowlist_row_properties(row.get("properties")),
                        }
                        for row in rows
                    ]
                }
            else:
                return ConnectorResult(
                    status="deny",
                    configured=True,
                    action=action,
                    detail="unknown_capability",
                )
        except NotionAPIError as exc:
            if exc.code == "not_configured":
                return ConnectorResult(
                    status="not_configured",
                    configured=False,
                    action=action,
                    detail=_NOT_CONFIGURED,
                )
            return ConnectorResult(
                status="deny",
                configured=True,
                action=action,
                detail=exc.code,
            )
        return ConnectorResult(
            status="ok",
            configured=True,
            action=action,
            detail="ok",
            payload=payload,
        )

    def _execute_write(self, action: str, clean: dict[str, Any]) -> dict[str, Any]:
        client = self._client_or_none()
        if client is None:
            return {"status": "not_configured"}
        if action == Scope.NOTION_CREATE_PAGE:
            created = client.create_page(_create_page_body(clean))
            return allowlist_fields(summarize_page(created), ("id", "url", "title"))
        if action == Scope.NOTION_APPEND_BLOCKS:
            page_id = str(clean["page_id"])
            blocks = clean.get("blocks") or []
            if not isinstance(blocks, list):
                raise PermissionError("invalid_blocks")
            client.append_blocks(page_id, blocks)
            return {"page_id": page_id, "appended": len(blocks)}
        if action == Scope.NOTION_UPDATE_PAGE_PROPERTY:
            page_id = str(clean["page_id"])
            name = str(clean["property_name"])
            ptype = str(clean["property_type"])
            updated = client.update_page(
                page_id, {name: _property_payload(ptype, clean.get("value"))}
            )
            return allowlist_fields(summarize_page(updated), ("id", "url", "title"))
        raise PermissionError("unknown_capability")


DEFAULT_NOTION_COLLAB_CONNECTOR = NotionCollabConnector()
