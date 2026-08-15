"""Identity attribution for traces (spec 30.2, §4044).

A Trace MUST capture:
  Requested by / Agent profile / Executed as / Connection / Approval
and the automation variant (triggered by / runbook / worker).

MUST enforce: never present a company-bot action as an employee's, or
vice versa. Automation MUST NEVER impersonate an employee (spec 15.6).
"""

from __future__ import annotations

from pydantic import BaseModel

from packages.authz.principals import EMPLOYEE_SLUGS, SERVICE_SLUG

_SHARED_PREFIXES = ("company/", "team:")
_PERSONAL_PREFIXES = ("user:",)
_BOT_SLUGS = frozenset(
    {
        SERVICE_SLUG,
        "company-hermes-bot",
        "company-crm-readonly",
        "company-github-bot",
        "company-marketing-bot",
    }
)


class TraceAttribution(BaseModel):
    """Spec 30.2 identity block. No secrets."""

    requested_by: str
    agent_profile: str
    executed_as: str
    connection: str | None = None
    approval: str | None = None
    triggered_by: str | None = None
    runbook: str | None = None
    worker: str | None = None


def _is_employee(slug: str) -> bool:
    return slug in EMPLOYEE_SLUGS


def _is_service(slug: str) -> bool:
    if slug in _BOT_SLUGS:
        return True
    if slug.startswith("schedule/"):
        return False
    return slug.startswith("company-") and not _is_employee(slug)


def _is_schedule(slug: str) -> bool:
    return slug.startswith("schedule/")


def _is_shared_connection(connection: str | None) -> bool:
    if not connection:
        return False
    return connection.startswith(_SHARED_PREFIXES)


def _is_personal_connection(connection: str | None) -> bool:
    if not connection:
        return False
    return connection.startswith(_PERSONAL_PREFIXES)


def attribution_consistent(
    requested_by: str,
    agent_profile: str,
    executed_as: str,
    connection: str | None,
    approval: str | None,
) -> bool:
    """Return True only when the 30.2 identity block is internally consistent.

    Pure function. Does not load credentials. `approval` may be an id or None
    (read-only / not required).
    """
    _ = approval
    if not requested_by or not agent_profile or not executed_as:
        return False

    requester_is_automation = _is_service(requested_by) or _is_schedule(requested_by)
    profile_is_automation = agent_profile == SERVICE_SLUG or agent_profile == "automation"

    # Never present a company-bot action as an employee's, or vice versa.
    if _is_employee(executed_as) and _is_shared_connection(connection):
        return False
    if _is_service(executed_as) and _is_personal_connection(connection):
        return False

    # Automation never impersonates an employee.
    if requester_is_automation and _is_employee(executed_as):
        return False
    if profile_is_automation and _is_employee(executed_as):
        return False

    # An employee may only execute-as themselves (no cross-user).
    if _is_employee(executed_as) and requested_by != executed_as:
        return False

    # Shared connection must execute as a service principal.
    if _is_shared_connection(connection) and not _is_service(executed_as):
        return False

    # Personal connection must execute as its owning employee.
    if _is_personal_connection(connection):
        if not _is_employee(executed_as):
            return False
        owner = connection.split(":", 1)[1].split("/", 1)[0]
        if executed_as != owner:
            return False

    return True


def attribution_from_parts(
    *,
    requested_by: str,
    agent_profile: str,
    executed_as: str,
    connection: str | None = None,
    approval: str | None = None,
    triggered_by: str | None = None,
    runbook: str | None = None,
    worker: str | None = None,
) -> TraceAttribution:
    if not attribution_consistent(
        requested_by, agent_profile, executed_as, connection, approval
    ):
        raise ValueError("attribution_inconsistent (spec 30.2 / §4044)")
    return TraceAttribution(
        requested_by=requested_by,
        agent_profile=agent_profile,
        executed_as=executed_as,
        connection=connection,
        approval=approval,
        triggered_by=triggered_by,
        runbook=runbook,
        worker=worker,
    )
