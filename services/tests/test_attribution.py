"""Trace attribution consistency (spec 30.2, 15.6, §4044)."""

from packages.authz.principals import SERVICE_SLUG
from packages.tracing.attribution import attribution_consistent


def test_employee_request_via_shared_bot_is_consistent():
    assert (
        attribution_consistent(
            requested_by="employee-b",
            agent_profile="employee-b",
            executed_as="company-hermes-bot",
            connection="company/github-hermes-bot",
            approval="apr_123",
        )
        is True
    )


def test_personal_connection_executes_as_the_employee():
    assert (
        attribution_consistent(
            requested_by="employee-a",
            agent_profile="employee-a",
            executed_as="employee-a",
            connection="user:employee-a/github-oauth",
            approval=None,
        )
        is True
    )


def test_never_present_bot_action_as_employee():
    assert (
        attribution_consistent(
            requested_by="employee-b",
            agent_profile="employee-b",
            executed_as="employee-b",
            connection="company/github-hermes-bot",
            approval="apr_123",
        )
        is False
    )


def test_never_present_employee_action_as_bot_on_personal_connection():
    assert (
        attribution_consistent(
            requested_by="employee-a",
            agent_profile="employee-a",
            executed_as="company-hermes-bot",
            connection="user:employee-a/github-oauth",
            approval=None,
        )
        is False
    )


def test_automation_never_impersonates_employee():
    assert (
        attribution_consistent(
            requested_by=SERVICE_SLUG,
            agent_profile="automation",
            executed_as="employee-a",
            connection="user:employee-a/github-oauth",
            approval=None,
        )
        is False
    )
    assert (
        attribution_consistent(
            requested_by="schedule/nightly-crm-hygiene",
            agent_profile="automation",
            executed_as="employee-a",
            connection="company/crm-readonly",
            approval=None,
        )
        is False
    )


def test_automation_readonly_schedule_is_consistent():
    assert (
        attribution_consistent(
            requested_by="schedule/nightly-crm-hygiene",
            agent_profile="automation",
            executed_as="company-crm-readonly",
            connection="company/crm-readonly",
            approval=None,
        )
        is True
    )


def test_cross_employee_execution_is_inconsistent():
    assert (
        attribution_consistent(
            requested_by="employee-a",
            agent_profile="employee-a",
            executed_as="employee-b",
            connection="user:employee-b/github-oauth",
            approval=None,
        )
        is False
    )
