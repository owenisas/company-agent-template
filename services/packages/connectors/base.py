"""Connector interface (spec 12.1, 13.2).

A connector MAY hold only its own system credentials. Phase 3 adds
read-only GitHub/CRM *typing* only (no clients). Concrete products
need D020–D024 / D042 / D051.

Default implementation is NOT-CONFIGURED and refuses every action.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from packages.tracing.context import RequestContext


class ConnectorAction(BaseModel):
    name: str
    risk_tier: str
    description: str
    preview_required: bool = False


class ConnectorResult(BaseModel):
    status: str
    configured: bool = False
    action: str
    detail: str
    payload: dict[str, Any] = Field(default_factory=dict)


class Connector:
    """Typed actions only. Credentials never enter Hermes context (spec 12.3)."""

    connection_id: str = "unconfigured"
    system: str = "none"

    def actions(self) -> list[ConnectorAction]:
        return []

    def invoke(
        self,
        action: str,
        ctx: RequestContext,
        params: dict[str, Any] | None = None,
    ) -> ConnectorResult:
        RequestContext.require(ctx)
        _ = params
        return ConnectorResult(
            status="not_configured",
            configured=False,
            action=action,
            detail=(
                f"TODO: no concrete connector for {self.connection_id} "
                "(Phase 3; D020-D024 data scope)"
            ),
        )


class NotConfiguredConnector(Connector):
    connection_id = "not-configured"
    system = "none"


DEFAULT_CONNECTOR = NotConfiguredConnector()
