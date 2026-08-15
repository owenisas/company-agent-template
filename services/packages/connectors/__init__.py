"""Connectors package (spec 13.2).

Read-only typing for GitHub, CRM, and Notion. Future company-context
importers are listed in README.md and FUTURE_CONNECTORS; they are not live.
"""

from packages.connectors.base import DEFAULT_CONNECTOR, Connector, ConnectorResult
from packages.connectors.crm_readonly import CRM_READONLY_ACTIONS
from packages.connectors.github_readonly import GITHUB_READONLY_ACTIONS
from packages.connectors.notion_readonly import (
    DEFAULT_NOTION_CONNECTOR,
    NOTION_READONLY_ACTIONS,
    NotionReadOnlyConnector,
)

FUTURE_CONNECTORS: tuple[str, ...] = (
    "google_drive",
    "google_docs",
    "slack",
    "confluence",
    "onedrive",
    "email",
)

CONNECTOR_REGISTRY: dict[str, str] = {
    "github_readonly": "packages.connectors.github_readonly",
    "crm_readonly": "packages.connectors.crm_readonly",
    "notion_readonly": "packages.connectors.notion_readonly",
}

__all__ = [
    "CONNECTOR_REGISTRY",
    "CRM_READONLY_ACTIONS",
    "DEFAULT_CONNECTOR",
    "DEFAULT_NOTION_CONNECTOR",
    "FUTURE_CONNECTORS",
    "GITHUB_READONLY_ACTIONS",
    "NOTION_READONLY_ACTIONS",
    "Connector",
    "ConnectorResult",
    "NotionReadOnlyConnector",
]
