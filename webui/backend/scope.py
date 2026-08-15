"""Profile access rules. Enforced on every API path that names a profile.

WebUI roles are a coarse projection of the governance roles in
`governance/user-role-group-registry.md`:

    owner    → admin   (this module: all host profiles, including automation)
    builder  → admin   for now; tighten later if builders should not run automation
    approver → user    for now; later: own profile plus named approval profiles
    viewer   → user    (own profile only; never automation)

`admin` is granted when the user record has role `admin` OR the username
appears in `WEBUI_ADMINS` (comma-separated). Non-admin restrictions are
intentionally easy to tighten here without touching the HTTP layer:
change `can_access` / `accessible_profiles` only.
"""

from __future__ import annotations

from .config import admins_from_env

ADMIN_ROLE = "admin"
USER_ROLES = frozenset({"user", "viewer", "builder", "approver"})


def is_automation_profile(name: str) -> bool:
    slug = (name or "").strip().lower()
    return slug == "automation" or slug.endswith("-automation")


def is_admin(username: str, role: str) -> bool:
    if (role or "").strip().lower() == ADMIN_ROLE:
        return True
    return username in admins_from_env()


def own_profile(user: dict) -> str:
    return (user.get("profile") or "").strip()


def can_access(user: dict, profile: str) -> bool:
    """Server-side gate. Never trust a client-supplied allow-list."""
    name = (profile or "").strip()
    if not name or not user:
        return False
    if is_admin(user.get("username", ""), user.get("role", "")):
        return True
    if is_automation_profile(name):
        return False
    return name == own_profile(user)


def accessible_profiles(user: dict, host_profiles: list[str]) -> list[str]:
    return [name for name in host_profiles if can_access(user, name)]
