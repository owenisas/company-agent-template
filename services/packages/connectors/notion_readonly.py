"""Notion read-only connector (company-context import).

Typed tools only. No client, no tokens, no network.
Secrets come from the deployment secret system only (D025 / D034).
Default state is NOT_CONFIGURED. Live Notion connect is TODO (D025).
"""

from __future__ import annotations

from typing import Any

from packages.connectors.base import Connector, ConnectorAction, ConnectorResult
from packages.tracing.context import RequestContext

PAGES_LIST_FIELDS: tuple[str, ...] = (
    "id",
    "title",
    "parent_id",
    "last_edited_time",
    "url",
)
DATABASES_LIST_FIELDS: tuple[str, ...] = (
    "id",
    "title",
    "parent_id",
    "last_edited_time",
    "url",
)
PAGE_READ_FIELDS: tuple[str, ...] = (
    "id",
    "title",
    "parent_id",
    "last_edited_time",
    "url",
    "plain_text",
)
COMMENTS_LIST_FIELDS: tuple[str, ...] = (
    "id",
    "page_id",
    "created_time",
    "plain_text",
)

NOTION_READONLY_ACTIONS: tuple[ConnectorAction, ...] = (
    ConnectorAction(
        name="pages.list",
        risk_tier="R0",
        description="List pages in an allowlisted Notion scope (allowlisted fields only).",
        preview_required=False,
    ),
    ConnectorAction(
        name="databases.list",
        risk_tier="R0",
        description="List databases in an allowlisted Notion scope (allowlisted fields only).",
        preview_required=False,
    ),
    ConnectorAction(
        name="page.read",
        risk_tier="R0",
        description="Read page content (allowlisted fields only).",
        preview_required=False,
    ),
    ConnectorAction(
        name="comments.list",
        risk_tier="R0",
        description="List comments on a page (allowlisted fields only).",
        preview_required=False,
    ),
)

TOOL_SCHEMAS: dict[str, dict[str, tuple[str, ...]]] = {
    "pages.list": {"params": ("scope_id",), "fields": PAGES_LIST_FIELDS},
    "databases.list": {"params": ("scope_id",), "fields": DATABASES_LIST_FIELDS},
    "page.read": {"params": ("page_id",), "fields": PAGE_READ_FIELDS},
    "comments.list": {"params": ("page_id",), "fields": COMMENTS_LIST_FIELDS},
}

_NOT_CONFIGURED = "not_configured — D025 Notion live-connect"


def allowlist_fields(payload: dict[str, Any], allowed: tuple[str, ...]) -> dict[str, Any]:
    """Return only keys present in the field allowlist. Pure logic; no I/O."""
    return {key: payload[key] for key in allowed if key in payload}


class NotionReadOnlyConnector(Connector):
    """Read-only Notion tools. Never holds a token or API key."""

    connection_id = "company/notion-readonly"
    system = "notion"
    configured = False

    def actions(self) -> list[ConnectorAction]:
        return list(NOTION_READONLY_ACTIONS)

    def invoke(
        self,
        action: str,
        ctx: RequestContext,
        params: dict[str, Any] | None = None,
    ) -> ConnectorResult:
        RequestContext.require(ctx)
        _ = params
        if action not in TOOL_SCHEMAS:
            return ConnectorResult(
                status="deny",
                configured=self.configured,
                action=action,
                detail="unknown_capability",
            )
        if not self.configured:
            return ConnectorResult(
                status="not_configured",
                configured=False,
                action=action,
                detail=_NOT_CONFIGURED,
                payload={"fields": list(TOOL_SCHEMAS[action]["fields"])},
            )
        return ConnectorResult(
            status="deny",
            configured=True,
            action=action,
            detail="live Notion client is TODO (D025); refusing to call a network",
        )


DEFAULT_NOTION_CONNECTOR = NotionReadOnlyConnector()
