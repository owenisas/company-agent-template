"""build_acl_clause produces the correct prefilter (spec 14.4)."""

from packages.authz.principals import Principal, PrincipalType, employee, service, system
from packages.knowledge.retrieval import (
    ACL_SESSION_MEMBERSHIPS,
    app_prefilter_allows,
    build_acl_clause,
    reciprocal_rank_fusion,
    sql_rls_claims_gate,
)


def test_employee_clause_binds_own_slug_and_blocks_other_private():
    a = employee("employee-a")
    clause = build_acl_clause(a, ["all-employees", "engineering"])
    assert "principal=employee-a" in clause
    assert "type=employee" in clause
    # owner_principal_id / scope_id are uuids (0005); slugs match via joins.
    assert "p.id = sources.owner_principal_id" in clause
    assert "p.external_id = :acl_principal_slug" in clause
    assert "owner_principal_id = :acl_principal_slug" not in clause
    assert "sc.id = sources.scope_id" in clause
    assert "sc.slug = ANY(:acl_memberships)" in clause
    assert "scope_slug" not in clause
    assert "deleted_at IS NULL" in clause
    assert "classification <> 'restricted'" in clause
    assert ACL_SESSION_MEMBERSHIPS in clause


def test_employee_with_restricted_membership_keeps_cross_user_private_block():
    a = employee("employee-a")
    clause = build_acl_clause(a, ["all-employees", "legal-approvers"])
    assert "p.id = sources.owner_principal_id" in clause
    assert "p.external_id = :acl_principal_slug" in clause
    # Restricted-domain members may see restricted company rows they are ACL'd
    # to, but still cannot see another employee's private notes.
    assert "classification <> 'restricted' OR owner_principal_id" not in clause
    assert "visibility = 'private'" in clause


def test_service_clause_excludes_private_and_restricted():
    bot = service()
    clause = build_acl_clause(bot, ["automation"])
    assert "type=service" in clause
    assert "visibility <> 'private'" in clause
    assert "classification <> 'restricted'" in clause
    assert "visibility IN ('team', 'project')" in clause
    assert "sc.id = sources.scope_id" in clause
    assert "sc.slug = ANY(:acl_memberships)" in clause
    assert "scope_slug" not in clause
    assert "employee-a" not in clause


def test_system_clause_still_hides_deleted():
    clause = build_acl_clause(system(), [])
    assert "type=system" in clause
    assert "deleted_at IS NULL" in clause


def test_unknown_slug_is_deniable_and_not_interpolated():
    bogus = Principal(slug="not-a-principal'; DROP TABLE sources; --", principal_type=PrincipalType.EMPLOYEE)
    clause = build_acl_clause(bogus, ["all-employees"])
    assert clause == "(FALSE)"
    assert "DROP" not in clause
    assert "not-a-principal" not in clause


def test_type_mismatch_slug_is_deniable():
    mismatch = Principal(slug="employee-a", principal_type=PrincipalType.SYSTEM)
    clause = build_acl_clause(mismatch, [])
    assert clause == "(FALSE)"
    assert "employee-a" not in clause


def test_rrf_fuses_ranks():
    fused = reciprocal_rank_fusion(["a", "b"], ["b", "c"])
    ids = [item_id for item_id, _ in fused]
    assert ids[0] == "b"
    assert set(ids) == {"a", "b", "c"}


# Visibility matrix: app prefilter and claims RLS gate must agree (no database).
_MATRIX = [
    (
        "own_private",
        employee("employee-a"),
        ["all-employees"],
        {"visibility": "private", "classification": "internal", "owner_slug": "employee-a"},
        True,
    ),
    (
        "other_private",
        employee("employee-a"),
        ["all-employees"],
        {"visibility": "private", "classification": "internal", "owner_slug": "employee-b"},
        False,
    ),
    (
        "company_public",
        employee("employee-a"),
        ["all-employees"],
        {"visibility": "company", "classification": "internal", "owner_slug": "employee-b"},
        True,
    ),
    (
        "team_member",
        employee("employee-a"),
        ["all-employees", "engineering"],
        {
            "visibility": "team",
            "classification": "internal",
            "owner_slug": "employee-b",
            "scope_slug": "engineering",
        },
        True,
    ),
    (
        "team_non_member",
        employee("employee-a"),
        ["all-employees", "engineering"],
        {
            "visibility": "team",
            "classification": "internal",
            "owner_slug": "employee-b",
            "scope_slug": "legal",
        },
        False,
    ),
    (
        "company_restricted_no_group",
        employee("employee-a"),
        ["all-employees"],
        {"visibility": "company", "classification": "restricted", "owner_slug": "employee-b"},
        False,
    ),
    (
        "company_restricted_with_group",
        employee("employee-a"),
        ["all-employees", "legal-approvers"],
        {"visibility": "company", "classification": "restricted", "owner_slug": "employee-b"},
        True,
    ),
    (
        "own_restricted_private",
        employee("employee-a"),
        ["all-employees"],
        {"visibility": "private", "classification": "restricted", "owner_slug": "employee-a"},
        True,
    ),
    (
        "restricted_source_acl",
        employee("employee-a"),
        ["all-employees"],
        {
            "visibility": "company",
            "classification": "restricted",
            "owner_slug": "employee-b",
            "acl_principal_slugs": ("employee-a",),
        },
        True,
    ),
    (
        "service_company",
        service(),
        ["automation"],
        {"visibility": "company", "classification": "internal", "owner_slug": "employee-a"},
        True,
    ),
    (
        "service_private",
        service(),
        ["automation"],
        {"visibility": "private", "classification": "internal", "owner_slug": "employee-a"},
        False,
    ),
    (
        "service_restricted",
        service(),
        ["automation"],
        {"visibility": "company", "classification": "restricted", "owner_slug": "employee-a"},
        False,
    ),
    (
        "service_team_member",
        service(),
        ["automation", "engineering"],
        {
            "visibility": "team",
            "classification": "internal",
            "owner_slug": "employee-b",
            "scope_slug": "engineering",
        },
        True,
    ),
    (
        "service_team_non_member",
        service(),
        ["automation"],
        {
            "visibility": "team",
            "classification": "internal",
            "owner_slug": "employee-b",
            "scope_slug": "engineering",
        },
        False,
    ),
    (
        "service_project_member",
        service(),
        ["automation", "example-team"],
        {
            "visibility": "project",
            "classification": "internal",
            "owner_slug": "employee-b",
            "scope_slug": "example-team",
        },
        True,
    ),
    (
        "service_project_non_member",
        service(),
        ["automation"],
        {
            "visibility": "project",
            "classification": "internal",
            "owner_slug": "employee-b",
            "scope_slug": "example-team",
        },
        False,
    ),
    (
        "system_other_private",
        system(),
        [],
        {"visibility": "private", "classification": "restricted", "owner_slug": "employee-b"},
        True,
    ),
    (
        "system_deleted",
        system(),
        [],
        {
            "visibility": "company",
            "classification": "internal",
            "owner_slug": "employee-a",
            "deleted_at": "2026-01-01",
        },
        False,
    ),
    (
        "quarantined_untrusted",
        employee("employee-a"),
        ["all-employees"],
        {
            "visibility": "company",
            "classification": "internal",
            "owner_slug": "employee-a",
            "status": "quarantined",
            "instruction_trust": "full",
        },
        False,
    ),
]


def test_app_prefilter_and_claims_gate_agree():
    for name, principal, memberships, source, expected in _MATRIX:
        app = app_prefilter_allows(principal, memberships, source)
        gate = sql_rls_claims_gate(principal, memberships, [source])
        assert app is expected, f"{name}: app={app} expected={expected}"
        assert gate is expected, f"{name}: gate={gate} expected={expected}"
        assert app is gate, f"{name}: app={app} gate={gate}"


def test_claims_gate_denies_empty_evidence():
    a = employee("employee-a")
    assert sql_rls_claims_gate(a, ["all-employees"], []) is False


def test_claims_gate_allows_if_any_evidence_source_readable():
    a = employee("employee-a")
    hidden = {"visibility": "private", "classification": "internal", "owner_slug": "employee-b"}
    visible = {"visibility": "company", "classification": "internal", "owner_slug": "employee-b"}
    assert sql_rls_claims_gate(a, ["all-employees"], [hidden]) is False
    assert sql_rls_claims_gate(a, ["all-employees"], [hidden, visible]) is True
    assert app_prefilter_allows(a, ["all-employees"], hidden) is False
    assert app_prefilter_allows(a, ["all-employees"], visible) is True
