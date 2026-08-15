"""Connection reference model (spec 12.1 credential classes, 15.4).

A personal connection reference lives in the PROFILE's
`connection-references/` directory and is never embedded in a prompt
or model context. The record points at a credential; it MUST NOT carry
the credential value.

On-disk format (scaffold default; production confirmation is D062):
YAML matching the spec 12.1 connection record.

TODO: D020–D024 concrete systems; D034 secrets product; D048 class choice.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class CredentialClass(str, Enum):
    """Spec 12.1."""

    PERSONAL = "personal"
    SHARED = "shared"
    DELEGATED = "delegated"


class ConnectionReference(BaseModel):
    """Pointer to a credential. Never the credential itself."""

    id: str
    plugin: str
    scope: str
    principal: str
    credential_ref: str = Field(description="URI such as secret://… — not a secret value")
    credential_class: CredentialClass
    allowed_actions: tuple[str, ...] = Field(default_factory=tuple)
    forbidden_actions: tuple[str, ...] = Field(default_factory=tuple)
    approval_policy: str = "none_for_allowed_actions"
    owner: str | None = None
    profile_path: str | None = Field(
        default=None,
        description="Relative path under the profile connection-references/ directory",
    )

    def secret_value(self) -> None:
        """References never expose a secret. Always None."""
        return None
