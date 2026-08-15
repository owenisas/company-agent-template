"""Zero-unauthorized-retrieval matrix as pure logic.

Spec Phase 2 exit: zero unauthorized retrieval.
Cases:
- employee A cannot read employee B's restricted scope
- automation cannot impersonate employee
- deny defaults (unknown capability, unknown connection)
"""

from packages.authz.policy import CAPABILITIES, is_allowed
from packages.authz.principals import employee, service, system
from packages.authz.scopes import Scope, WRITE_SCOPES_BY_TIER


def test_employee_a_cannot_read_employee_b_restricted():
    a = employee("employee-a")
    decision = is_allowed(
        a,
        ["all-employees"],
        "user:employee-b/restricted",
        "R0",
        False,
    )
    assert decision.effect == "deny"
    assert decision.reason == "cross_user_restricted_denied"
    assert decision.allowed is False


def test_employee_a_cannot_read_employee_b_private():
    a = employee("employee-a")
    decision = is_allowed(a, ["all-employees"], "user:employee-b/private", "R0", False)
    assert decision.effect == "deny"


def test_employee_a_can_read_own_restricted():
    a = employee("employee-a")
    decision = is_allowed(a, ["all-employees"], "user:employee-a/restricted", "R0", False)
    assert decision.effect == "allow"
    assert decision.reason == "owner_self_scope"


def test_automation_cannot_impersonate_employee_private():
    bot = service()
    decision = is_allowed(
        bot,
        ["automation", "all-employees"],
        "user:employee-a/private",
        "R0",
        False,
    )
    assert decision.effect == "deny"
    assert decision.reason == "automation_never_impersonates"


def test_automation_cannot_hold_impersonate_scope():
    bot = service()
    decision = is_allowed(bot, ["automation"], Scope.IDENTITY_IMPERSONATE, "R4", True)
    assert decision.effect == "deny"
    assert decision.reason == "automation_never_impersonates"


def test_automation_cannot_use_personal_github_oauth():
    bot = service()
    decision = is_allowed(
        bot,
        ["automation"],
        "user:employee-a/github-oauth",
        "R1",
        False,
    )
    assert decision.effect == "deny"
    assert decision.reason == "automation_never_impersonates"


def test_unknown_capability_denied():
    a = employee("employee-a")
    decision = is_allowed(a, ["all-employees"], "no.such.capability", "R0", False)
    assert decision.effect == "deny"
    assert decision.reason == "unknown_capability"


def test_unknown_connection_denied():
    a = employee("employee-a")
    decision = is_allowed(a, ["all-employees"], "company/unknown-saas", "R0", False)
    assert decision.effect == "deny"
    assert decision.reason == "unknown_connection"


def test_signing_denied_even_for_employees():
    a = employee("employee-a")
    decision = is_allowed(a, ["legal-approvers"], Scope.CONTRACTS_SIGN, "R4", True)
    assert decision.effect == "deny"
    assert decision.reason == "capability_denied"


def test_payment_denied():
    a = employee("employee-a")
    decision = is_allowed(a, ["finance-approvers"], Scope.FINANCE_PAYMENT, "R4", True)
    assert decision.effect == "deny"


def test_knowledge_search_allowed_for_employee():
    a = employee("employee-a")
    decision = is_allowed(a, ["all-employees"], Scope.KNOWLEDGE_SEARCH, "R0", False)
    assert decision.effect == "allow"


def test_knowledge_search_denied_for_automation_without_employee_group_abuse():
    """36.1 lists all-employees. Service is not an employee (spec 15.3)."""
    bot = service()
    decision = is_allowed(bot, ["automation"], Scope.KNOWLEDGE_SEARCH, "R0", False)
    assert decision.effect == "deny"
    assert decision.reason == "group_not_permitted"


def test_promote_claim_requires_approval():
    a = employee("employee-a")
    decision = is_allowed(a, ["research"], Scope.KNOWLEDGE_PROMOTE_CLAIM, "R2", False)
    assert decision.effect == "approval_required"


def test_inactive_principal_denied():
    a = employee("employee-a")
    a = a.model_copy(update={"active": False})
    decision = is_allowed(a, ["all-employees"], Scope.KNOWLEDGE_SEARCH, "R0", False)
    assert decision.effect == "deny"
    assert decision.reason == "principal_inactive"


def test_system_may_read_restricted_for_propagation():
    sys = system()
    decision = is_allowed(sys, [], "user:employee-b/restricted", "R0", False)
    assert decision.effect == "allow"
    assert decision.reason == "system_control_plane"


def test_capabilities_tier_matches_write_scopes_bucket():
    """Every CAPABILITIES scope must sit in the matching WRITE_SCOPES_BY_TIER bucket."""
    bucket_of: dict[str, object] = {}
    for tier, scopes in WRITE_SCOPES_BY_TIER.items():
        for scope in scopes:
            assert scope not in bucket_of, f"{scope} listed in both {bucket_of[scope]} and {tier}"
            bucket_of[scope] = tier

    missing = [scope for scope in CAPABILITIES if scope not in bucket_of]
    mismatched = [
        (scope, CAPABILITIES[scope]["risk"], bucket_of[scope])
        for scope in CAPABILITIES
        if scope in bucket_of and bucket_of[scope] != CAPABILITIES[scope]["risk"]
    ]
    assert missing == [], f"CAPABILITIES scopes missing from WRITE_SCOPES_BY_TIER: {missing}"
    assert mismatched == [], f"tier mismatch (scope, capabilities, bucket): {mismatched}"
    assert CAPABILITIES[Scope.GITHUB_PROTECTED_MERGE]["risk"].value == "R3"
    assert Scope.GITHUB_PROTECTED_MERGE in WRITE_SCOPES_BY_TIER[CAPABILITIES[Scope.GITHUB_PROTECTED_MERGE]["risk"]]
