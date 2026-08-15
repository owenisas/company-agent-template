"""GitHub read-only connector typing (spec 12.1, 13.2, §3876).

Schemas only. No client, no secrets, no network.
Concrete product/org binding is TODO (D042, D051).
"""

from __future__ import annotations

from packages.connectors.base import ConnectorAction

# Field allowlists (D063 until D042/D020 close).
REPO_METADATA_FIELDS: tuple[str, ...] = (
    "full_name",
    "default_branch",
    "private",
    "description",
    "html_url",
)
FILE_READ_FIELDS: tuple[str, ...] = ("path", "sha", "size", "encoding", "type")
ISSUES_LIST_FIELDS: tuple[str, ...] = ("number", "title", "state", "html_url", "updated_at")

GITHUB_READONLY_ACTIONS: tuple[ConnectorAction, ...] = (
    ConnectorAction(
        name="repo.metadata",
        risk_tier="R0",
        description="Read repository metadata (allowlisted fields only).",
        preview_required=False,
    ),
    ConnectorAction(
        name="file.read",
        risk_tier="R0",
        description="Read a file blob metadata (allowlisted fields only).",
        preview_required=False,
    ),
    ConnectorAction(
        name="issues.list",
        risk_tier="R0",
        description="List issues (allowlisted fields only).",
        preview_required=False,
    ),
)

TOOL_SCHEMAS: dict[str, dict[str, tuple[str, ...]]] = {
    "repo.metadata": {"params": ("owner", "repo"), "fields": REPO_METADATA_FIELDS},
    "file.read": {"params": ("owner", "repo", "path", "ref"), "fields": FILE_READ_FIELDS},
    "issues.list": {"params": ("owner", "repo", "state"), "fields": ISSUES_LIST_FIELDS},
}
