"""Principal types.

Normative: spec 4.2, 11.3, 15.3–15.6; governance user-role-group-registry.md.

Immutable slugs are the only identifiers. Display names MUST NOT be used as IDs
(spec 11.3). Real-world name/email bindings remain TODO (D001–D004).
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class PrincipalType(str, Enum):
    """Who is asking (spec 4.2 question 1)."""

    EMPLOYEE = "employee"
    SERVICE = "service"
    SYSTEM = "system"


EMPLOYEE_SLUGS: frozenset[str] = frozenset(
    {
        "employee-a",
        "employee-b",
        "employee-c",
    }
)

SERVICE_SLUG = "automation"
SYSTEM_SLUG = "company-system"

KNOWN_SLUGS: frozenset[str] = EMPLOYEE_SLUGS | {SERVICE_SLUG, SYSTEM_SLUG}


class Principal(BaseModel):
    """Authenticated actor. Authority and storage are separate (spec 4.2)."""

    slug: str
    principal_type: PrincipalType
    display_name: str | None = Field(
        default=None,
        description="Non-identifying label only. MUST NOT be used in ACLs.",
    )
    active: bool = True

    @property
    def is_employee(self) -> bool:
        return self.principal_type is PrincipalType.EMPLOYEE

    @property
    def is_service(self) -> bool:
        return self.principal_type is PrincipalType.SERVICE

    @property
    def is_system(self) -> bool:
        return self.principal_type is PrincipalType.SYSTEM

    def employee_private_scope(self) -> str:
        return f"user:{self.slug}/private"

    def employee_restricted_scope(self) -> str:
        return f"user:{self.slug}/restricted"


def employee(slug: str) -> Principal:
    if slug not in EMPLOYEE_SLUGS:
        raise ValueError(f"unknown employee slug: {slug}")
    return Principal(slug=slug, principal_type=PrincipalType.EMPLOYEE)


def service(slug: str = SERVICE_SLUG) -> Principal:
    if slug != SERVICE_SLUG:
        raise ValueError(f"unknown service slug: {slug}")
    return Principal(
        slug=slug,
        principal_type=PrincipalType.SERVICE,
        display_name="<Company> company automation",
    )


def system() -> Principal:
    return Principal(
        slug=SYSTEM_SLUG,
        principal_type=PrincipalType.SYSTEM,
        display_name="Control-plane system",
    )


def parse_principal(slug: str) -> Principal:
    if slug in EMPLOYEE_SLUGS:
        return employee(slug)
    if slug == SERVICE_SLUG:
        return service()
    if slug == SYSTEM_SLUG:
        return system()
    raise ValueError(f"unknown principal slug: {slug}")
