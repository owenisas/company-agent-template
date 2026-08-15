"""CRM read-only connector typing (spec 12.1, 13.2, §3876).

Schemas only. No client, no secrets, no network.
`<CRM_NAME>` and object/field scope are TODO (D020).
"""

from __future__ import annotations

from packages.connectors.base import ConnectorAction

RECORD_READ_FIELDS: tuple[str, ...] = ("id", "name", "owner", "updated_at")
STAGE_GET_FIELDS: tuple[str, ...] = ("id", "stage", "amount_band")
RENEWAL_READ_FIELDS: tuple[str, ...] = ("id", "renewal_date", "risk_flag")

CRM_READONLY_ACTIONS: tuple[ConnectorAction, ...] = (
    ConnectorAction(
        name="record.read",
        risk_tier="R0",
        description="Read one CRM record (allowlisted fields only).",
        preview_required=False,
    ),
    ConnectorAction(
        name="stage.get",
        risk_tier="R0",
        description="Read opportunity stage (allowlisted fields only).",
        preview_required=False,
    ),
    ConnectorAction(
        name="renewal.read",
        risk_tier="R0",
        description="Read renewal risk flag (allowlisted fields only).",
        preview_required=False,
    ),
)

TOOL_SCHEMAS: dict[str, dict[str, tuple[str, ...]]] = {
    "record.read": {"params": ("record_id",), "fields": RECORD_READ_FIELDS},
    "stage.get": {"params": ("opportunity_id",), "fields": STAGE_GET_FIELDS},
    "renewal.read": {"params": ("account_id",), "fields": RENEWAL_READ_FIELDS},
}
