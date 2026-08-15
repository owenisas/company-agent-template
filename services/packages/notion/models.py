"""Typed Notion OAuth and API records. Secret values never appear in public views."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class NotionConfig(BaseModel):
    """Public-connection app credentials. Never send these to a browser."""

    model_config = ConfigDict(frozen=True)

    client_id: str = ""
    client_secret: str = ""
    redirect_uri: str = ""
    token_path: str = ""

    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret and self.redirect_uri)

    def public_dict(self) -> dict[str, Any]:
        return {
            "client_id_set": bool(self.client_id),
            "client_secret_set": bool(self.client_secret),
            "redirect_uri": self.redirect_uri,
            "configured": self.configured,
        }


class NotionTokens(BaseModel):
    """Server-held grant. Public dumps omit token values."""

    workspace_id: str = ""
    workspace_name: str = ""
    workspace_icon: str | None = None
    bot_id: str = ""
    owner_id: str = ""
    owner_name: str = ""
    token_type: str = "bearer"
    duplicated_template_id: str | None = None
    updated_at: datetime = Field(default_factory=utcnow)
    raw_extra: dict[str, Any] = Field(default_factory=dict)

    _access_token: str = PrivateAttr(default="")
    _refresh_token: str = PrivateAttr(default="")

    @classmethod
    def from_oauth_payload(cls, payload: dict[str, Any]) -> "NotionTokens":
        owner = payload.get("owner") or {}
        user = owner.get("user") if isinstance(owner, dict) else {}
        if not isinstance(user, dict):
            user = {}
        tokens = cls(
            workspace_id=str(payload.get("workspace_id") or ""),
            workspace_name=str(payload.get("workspace_name") or ""),
            workspace_icon=payload.get("workspace_icon"),
            bot_id=str(payload.get("bot_id") or ""),
            owner_id=str(user.get("id") or ""),
            owner_name=str(user.get("name") or ""),
            token_type=str(payload.get("token_type") or "bearer"),
            duplicated_template_id=payload.get("duplicated_template_id"),
            updated_at=utcnow(),
            raw_extra={
                k: v
                for k, v in payload.items()
                if k
                not in {
                    "access_token",
                    "refresh_token",
                    "workspace_id",
                    "workspace_name",
                    "workspace_icon",
                    "bot_id",
                    "owner",
                    "token_type",
                    "duplicated_template_id",
                }
            },
        )
        tokens._access_token = str(payload.get("access_token") or "")
        tokens._refresh_token = str(payload.get("refresh_token") or "")
        return tokens

    @property
    def access_token(self) -> str:
        return self._access_token

    @property
    def refresh_token(self) -> str:
        return self._refresh_token

    def has_access_token(self) -> bool:
        return bool(self._access_token)

    def to_disk(self) -> dict[str, Any]:
        return {
            "access_token": self._access_token,
            "refresh_token": self._refresh_token,
            "workspace_id": self.workspace_id,
            "workspace_name": self.workspace_name,
            "workspace_icon": self.workspace_icon,
            "bot_id": self.bot_id,
            "owner_id": self.owner_id,
            "owner_name": self.owner_name,
            "token_type": self.token_type,
            "duplicated_template_id": self.duplicated_template_id,
            "updated_at": self.updated_at.isoformat(),
            "raw_extra": self.raw_extra,
        }

    @classmethod
    def from_disk(cls, payload: dict[str, Any]) -> "NotionTokens":
        updated = payload.get("updated_at")
        if isinstance(updated, str):
            try:
                parsed = datetime.fromisoformat(updated)
            except ValueError:
                parsed = utcnow()
        else:
            parsed = utcnow()
        tokens = cls(
            workspace_id=str(payload.get("workspace_id") or ""),
            workspace_name=str(payload.get("workspace_name") or ""),
            workspace_icon=payload.get("workspace_icon"),
            bot_id=str(payload.get("bot_id") or ""),
            owner_id=str(payload.get("owner_id") or ""),
            owner_name=str(payload.get("owner_name") or ""),
            token_type=str(payload.get("token_type") or "bearer"),
            duplicated_template_id=payload.get("duplicated_template_id"),
            updated_at=parsed,
            raw_extra=dict(payload.get("raw_extra") or {}),
        )
        tokens._access_token = str(payload.get("access_token") or "")
        tokens._refresh_token = str(payload.get("refresh_token") or "")
        return tokens

    def public_status(self) -> dict[str, Any]:
        return {
            "connected": self.has_access_token(),
            "workspace_id": self.workspace_id,
            "workspace_name": self.workspace_name,
            "bot_id": self.bot_id,
            "owner_id": self.owner_id,
            "owner_name": self.owner_name,
            "updated_at": self.updated_at.isoformat(),
        }


class NotionConnectionStatus(BaseModel):
    connected: bool = False
    configured: bool = False
    workspace_name: str | None = None
    workspace_id: str | None = None
    bot_id: str | None = None
    owner_name: str | None = None
    detail: str = ""

    def public_dict(self) -> dict[str, Any]:
        return self.model_dump()


class NotionOAuthState(BaseModel):
    state: str
    created_at: datetime = Field(default_factory=utcnow)
    return_to: str = "/"
