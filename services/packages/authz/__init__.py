"""Authorization primitives (spec 4.2, 13.3, 36.1)."""

from packages.authz.policy import Decision, is_allowed
from packages.authz.principals import (
    EMPLOYEE_SLUGS,
    SERVICE_SLUG,
    SYSTEM_SLUG,
    Principal,
    PrincipalType,
)
from packages.authz.scopes import Scope

__all__ = [
    "Decision",
    "EMPLOYEE_SLUGS",
    "Principal",
    "PrincipalType",
    "SERVICE_SLUG",
    "SYSTEM_SLUG",
    "Scope",
    "is_allowed",
]
