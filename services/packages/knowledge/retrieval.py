"""Hybrid search skeleton.

Normative: spec 6 retrieval row, 14.1, 14.4.

Flow MUST be: authenticate → memberships → authorized set → lexical/vector
inside that set → reciprocal-rank fusion → excerpts with provenance.

Authorization happens BEFORE retrieval (spec 14.4). build_acl_clause is a
pure function so the prefilter is unit-testable without a database.

Visibility model (must match migrations/0009_rls.sql):
  owner-private / team-project scope / company-public / restricted-with-source_acl
App prefilter is authoritative; RLS is defense in depth.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from packages.authz.principals import (
    EMPLOYEE_SLUGS,
    SERVICE_SLUG,
    SYSTEM_SLUG,
    Principal,
    PrincipalType,
)
from packages.authz.scopes import is_employee_scope


RESTRICTED_MEMBERSHIPS = frozenset(
    {
        "legal-approvers",
        "finance-approvers",
        "people-hr-approvers",
        "customer-data-approvers",
        "agent-platform-admins",
    }
)

# Session GUCs the app MUST SET LOCAL before any query. Bind params
# :acl_principal_slug / :acl_memberships carry the same values in the
# prefilter; the names below are what RLS reads (see 0009_rls.sql).
ACL_SESSION_PRINCIPAL_SLUG = "request.principal_slug"
ACL_SESSION_PRINCIPAL_TYPE = "request.principal_type"
ACL_SESSION_MEMBERSHIPS = "acl.memberships"

_DENIED_CLAUSE = "(FALSE)"

# Runtime table: sources (migrations/0005). Columns this fragment is rendered
# against — never compare uuid columns to slug binds:
#   sources.id uuid
#   sources.owner_principal_id uuid  → principals.id / principals.external_id
#   sources.scope_id uuid            → scopes.id / scopes.slug
#   sources.visibility, classification, deleted_at, status, instruction_trust
# Binds stay slugs: :acl_principal_slug, :acl_memberships.
# Not a standalone executable query until D055 (postgres host / kb_app).
_OWNER_IS_PRINCIPAL = (
    "EXISTS ("
    "SELECT 1 FROM principals p "
    "WHERE p.id = sources.owner_principal_id "
    "AND p.external_id = :acl_principal_slug"
    ")"
)
_SCOPE_IN_MEMBERSHIPS = (
    "EXISTS ("
    "SELECT 1 FROM scopes sc "
    "WHERE sc.id = sources.scope_id "
    "AND sc.slug = ANY(:acl_memberships)"
    ")"
)


def _principal_type_for_slug(slug: str) -> PrincipalType | None:
    if slug in EMPLOYEE_SLUGS:
        return PrincipalType.EMPLOYEE
    if slug == SERVICE_SLUG:
        return PrincipalType.SERVICE
    if slug == SYSTEM_SLUG:
        return PrincipalType.SYSTEM
    return None


def _validated_principal(principal: Principal) -> bool:
    """True only for a known slug whose type matches the enum."""
    expected = _principal_type_for_slug(principal.slug)
    return expected is not None and principal.principal_type is expected


def build_acl_clause(principal: Principal, memberships: Iterable[str]) -> str:
    """Return a SQL WHERE fragment.

    Bind parameters used (never interpolate caller strings into identifiers):
      :acl_principal_slug
      :acl_memberships          -- text[]
    Restricted classification is only visible when the principal holds a
    restricted-domain membership, is the owner, or has a source_acl grant.
    Service principals never match user-private rows (spec 15.3, 29.1).

    Unknown or type-mismatched slugs return a deniable (FALSE) clause and
    never appear in the emitted SQL.
    """
    if not _validated_principal(principal):
        return _DENIED_CLAUSE

    groups = frozenset(memberships)
    has_restricted = bool(groups & RESTRICTED_MEMBERSHIPS)

    # Parameterized fragment. Tests assert tokens, not a live plan.
    parts = [
        "deleted_at IS NULL",
        "status NOT IN ('deleted')",
        # Deleted/restricted sources must not be retrieved (Phase 2 exit).
        "NOT (status = 'quarantined' AND instruction_trust <> 'none')",
    ]

    if principal.principal_type is PrincipalType.SYSTEM:
        parts.append("TRUE /* system control-plane; still respects deleted_at */")
    elif principal.principal_type is PrincipalType.SERVICE:
        # Same rule as employees for team/project: membership required.
        # company/public stay open; private + restricted stay deny.
        parts.append(
            "("
            "visibility IN ('company', 'public') "
            f"OR (visibility IN ('team', 'project') AND {_SCOPE_IN_MEMBERSHIPS})"
            ")"
        )
        parts.append("visibility <> 'private'")
        parts.append("classification <> 'restricted'")
    else:
        # Employee: own private + membership scopes + company/public + source_acl.
        parts.append(
            "("
            f"{_OWNER_IS_PRINCIPAL}"
            " OR visibility IN ('company', 'public')"
            f" OR (visibility IN ('team', 'project') AND {_SCOPE_IN_MEMBERSHIPS})"
            " OR EXISTS ("
            "SELECT 1 FROM source_acl a "
            "JOIN principals p ON p.id = a.subject_id "
            "WHERE a.source_id = sources.id "
            "AND a.subject_type = 'principal' "
            "AND a.permission IN ('read', 'annotate', 'curate', 'admin') "
            "AND p.external_id = :acl_principal_slug"
            ")"
            " OR EXISTS ("
            "SELECT 1 FROM source_acl a "
            "JOIN scopes sc ON sc.id = a.subject_id "
            "WHERE a.source_id = sources.id "
            "AND a.subject_type = 'scope' "
            "AND a.permission IN ('read', 'annotate', 'curate', 'admin') "
            "AND sc.slug = ANY(:acl_memberships)"
            ")"
            ")"
        )
        if not has_restricted:
            parts.append(
                "("
                "classification <> 'restricted' "
                f"OR {_OWNER_IS_PRINCIPAL} "
                "OR EXISTS ("
                "SELECT 1 FROM source_acl a "
                "JOIN principals p ON p.id = a.subject_id "
                "WHERE a.source_id = sources.id "
                "AND a.subject_type = 'principal' "
                "AND a.permission IN ('read', 'annotate', 'curate', 'admin') "
                "AND p.external_id = :acl_principal_slug"
                ")"
                ")"
            )
        # Cross-user private/restricted: never expand to another employee's private.
        parts.append(
            f"NOT (visibility = 'private' AND NOT {_OWNER_IS_PRINCIPAL})"
        )

    clause = " AND ".join(parts)
    # Comment uses only the validated known slug / enum value — never raw input.
    return (
        f"/* principal={principal.slug} type={principal.principal_type.value} "
        f"guc={ACL_SESSION_MEMBERSHIPS} */ ({clause})"
    )


def _source_base_hidden(source: Mapping[str, Any]) -> bool:
    if source.get("deleted_at") is not None:
        return True
    if source.get("status", "active") in {"deleted"}:
        return True
    if source.get("status") == "quarantined" and source.get("instruction_trust", "none") != "none":
        return True
    return False


def _has_source_acl(principal: Principal, memberships: Iterable[str], source: Mapping[str, Any]) -> bool:
    if principal.slug in frozenset(source.get("acl_principal_slugs") or ()):
        return True
    granted_scopes = frozenset(source.get("acl_scope_slugs") or ())
    return bool(granted_scopes & frozenset(memberships))


def app_prefilter_allows(
    principal: Principal,
    memberships: Iterable[str],
    source: Mapping[str, Any],
) -> bool:
    """Evaluate build_acl_clause as logic (no SQL). App-layer authority."""
    if not _validated_principal(principal):
        return False
    if _source_base_hidden(source):
        return False

    groups = frozenset(memberships)
    visibility = source.get("visibility", "private")
    classification = source.get("classification", "internal")
    owner = source.get("owner_slug")
    scope_slug = source.get("scope_slug")
    is_owner = owner == principal.slug
    has_restricted = bool(groups & RESTRICTED_MEMBERSHIPS)
    acl_hit = _has_source_acl(principal, groups, source)

    if principal.principal_type is PrincipalType.SYSTEM:
        return True

    if principal.principal_type is PrincipalType.SERVICE:
        if classification == "restricted":
            return False
        if visibility in {"company", "public"}:
            return True
        if visibility in {"team", "project"}:
            return scope_slug in groups
        return False

    # employee
    if visibility == "private" and not is_owner:
        return False
    in_team_project = visibility in {"team", "project"} and scope_slug in groups
    in_company_public = visibility in {"company", "public"}
    if not (is_owner or in_company_public or in_team_project or acl_hit):
        return False
    if classification == "restricted" and not (is_owner or has_restricted or acl_hit):
        return False
    return True


def sql_rls_source_visible(
    principal: Principal,
    memberships: Iterable[str],
    source: Mapping[str, Any],
) -> bool:
    """Python mirror of source_row_readable() in 0009_rls.sql. No database."""
    if not _validated_principal(principal):
        return False
    if _source_base_hidden(source):
        return False

    groups = list(memberships)
    groupset = frozenset(groups)
    visibility = source.get("visibility", "private")
    classification = source.get("classification", "internal")
    owner = source.get("owner_slug")
    scope_slug = source.get("scope_slug")
    is_owner = owner == principal.slug
    p_type = principal.principal_type.value
    acl_hit = _has_source_acl(principal, groupset, source)
    scope_hit = visibility in {"team", "project"} and scope_slug in groupset
    company_public = visibility in {"company", "public"}
    restricted_member = bool(groupset & RESTRICTED_MEMBERSHIPS)

    if p_type == "system":
        return True

    allow = is_owner or company_public or scope_hit or acl_hit
    private_block = visibility == "private" and not is_owner and p_type != "system"
    service_block = p_type == "service" and (visibility == "private" or classification == "restricted")
    restricted_ok = (
        classification != "restricted"
        or is_owner
        or restricted_member
        or acl_hit
    )
    return allow and not private_block and not service_block and restricted_ok


def sql_rls_claims_gate(
    principal: Principal,
    memberships: Iterable[str],
    evidence_sources: Iterable[Mapping[str, Any]],
) -> bool:
    """Mirror of can_read_claim() / claims_select_via_evidence.

    A claim is readable iff at least one evidence source is readable under
    the same visibility model (claim_evidence → chunks → sources). No
    evidence ⇒ deny. Logic only; no database.
    """
    sources = list(evidence_sources)
    if not sources:
        return False
    return any(sql_rls_source_visible(principal, memberships, src) for src in sources)


def reciprocal_rank_fusion(
    lexical_ids: list[str],
    vector_ids: list[str],
    k: int = 60,
) -> list[tuple[str, float]]:
    """RRF (spec 6 / 14.1). Pure ranking; no I/O."""
    scores: dict[str, float] = {}
    for rank, item_id in enumerate(lexical_ids, start=1):
        scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
    for rank, item_id in enumerate(vector_ids, start=1):
        scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)


def hybrid_search_stub(
    principal: Principal,
    memberships: list[str],
    query: str,
) -> dict:
    """Not configured: returns structure only."""
    _ = query
    return {
        "status": "not_configured",
        "reason": "TODO: D055 postgres host; D040 embedding provider",
        "acl_clause": build_acl_clause(principal, memberships),
        "mode": "hybrid",
        "hits": [],
        "employee_scope_leak": any(
            is_employee_scope(m) and not m.endswith(principal.slug) for m in memberships
        ),
    }
