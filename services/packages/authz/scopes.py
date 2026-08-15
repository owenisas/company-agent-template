"""Scope constants.

Derived from:
- spec 12.5 risk tiers, 36.1 capabilities.yaml
- governance/integration-inventory.md (read scopes per connection)
- governance/action-approval-matrix.md (write/approve scopes per risk tier)

Connection IDs that are still TODO (D020–D024) are named but MUST NOT be
treated as authorized production connections.
"""

from __future__ import annotations

from enum import Enum


class RiskTier(str, Enum):
    """Spec 12.5 / action-approval-matrix §2."""

    R0 = "R0"  # read
    R1 = "R1"  # reversible internal
    R2 = "R2"  # external / reputational
    R3 = "R3"  # contractual / financial / production
    R4 = "R4"  # irreversible / high impact


class Scope:
    """Capability and connection scope names. Strings are the wire values."""

    # --- knowledge (company/knowledge-api, planned Phase 2) ---
    KNOWLEDGE_SEARCH = "knowledge.search"
    KNOWLEDGE_RETRIEVE_SOURCE = "knowledge.retrieve_source"
    KNOWLEDGE_INGEST = "knowledge.ingest"
    KNOWLEDGE_INGEST_DRY_RUN = "knowledge.ingest_dry_run"
    KNOWLEDGE_PROMOTE_CLAIM = "knowledge.promote_company_claim"
    KNOWLEDGE_FORGET = "knowledge.forget_or_restrict"

    # --- GitHub ---
    GITHUB_READ = "github.read"
    GITHUB_PR_CREATE = "github.pull_request.create"
    GITHUB_PROTECTED_MERGE = "github.protected_branch.merge"

    # --- CRM (D020 open; blocked-unknown-scope) ---
    CRM_ACCOUNT_READ = "crm.account.read"
    CRM_OPPORTUNITY_UPDATE = "crm.opportunity.update"
    CRM_BULK_EXPORT = "crm.bulk_export"

    # --- contracts / legal (D021 open) ---
    CONTRACTS_READ = "legal.contract.read"
    CONTRACTS_SIGN = "legal.contract.sign"

    # --- finance (D022 open) ---
    FINANCE_READ = "finance.record.read"
    FINANCE_PAYMENT = "finance.payment.execute"

    # --- publishing (D023/D024 open; autonomous send disabled) ---
    PUBLISHING_READ = "publishing.read"
    PUBLISHING_SEND = "publishing.company.send"

    # --- Discord (present-ungoverned; not approval SoR unless D027) ---
    DISCORD_READ = "discord.channel.read"
    DISCORD_SEND = "discord.message.send"

    # --- approval / audit / admin ---
    APPROVAL_REQUEST = "approval.request"
    APPROVAL_DECIDE = "approval.decide"
    AUDIT_APPEND = "audit.append"
    AUDIT_READ = "audit.read"
    ADMIN_PLATFORM = "platform.admin"

    # --- identity / employee-only ---
    IDENTITY_IMPERSONATE = "identity.impersonate"
    MEMORY_WRITE_PERSONAL = "memory.write.personal"

    # --- connection IDs (inventory §2; illustrative until D020–D024) ---
    CONN_KNOWLEDGE = "company/knowledge-api"
    CONN_POSTGRES = "company/postgres"
    CONN_RAW_OBJECTS = "company/raw-objects"
    CONN_KNOWLEDGE_MCP = "company/knowledge-mcp"
    CONN_APPROVAL_API = "company/approval-api"
    CONN_GITHUB_BOT = "company/github-hermes-bot"
    CONN_GITHUB_OAUTH_PREFIX = "user:*/github-oauth"
    CONN_CRM_READONLY = "company/crm-readonly"
    CONN_CRM_WRITE = "team:revenue/crm-automation"
    CONN_CONTRACTS = "company/contracts"
    CONN_FINANCE = "company/finance-readonly"
    CONN_EMAIL = "company/email-platform"
    CONN_SOCIAL = "company/social-brand"
    CONN_DISCORD = "company/discord-gateway"


# Read scopes per inventoried connection (R0 default).
CONNECTION_READ_SCOPES: dict[str, str] = {
    Scope.CONN_KNOWLEDGE: Scope.KNOWLEDGE_SEARCH,
    Scope.CONN_KNOWLEDGE_MCP: Scope.KNOWLEDGE_RETRIEVE_SOURCE,
    Scope.CONN_GITHUB_BOT: Scope.GITHUB_READ,
    Scope.CONN_CRM_READONLY: Scope.CRM_ACCOUNT_READ,
    Scope.CONN_CONTRACTS: Scope.CONTRACTS_READ,
    Scope.CONN_FINANCE: Scope.FINANCE_READ,
    Scope.CONN_EMAIL: Scope.PUBLISHING_READ,
    Scope.CONN_SOCIAL: Scope.PUBLISHING_READ,
    Scope.CONN_DISCORD: Scope.DISCORD_READ,
    Scope.CONN_APPROVAL_API: Scope.APPROVAL_REQUEST,
}

# Write / approve scopes by risk tier (matrix §3).
WRITE_SCOPES_BY_TIER: dict[RiskTier, frozenset[str]] = {
    RiskTier.R0: frozenset(
        {
            Scope.KNOWLEDGE_SEARCH,
            Scope.KNOWLEDGE_RETRIEVE_SOURCE,
            Scope.KNOWLEDGE_INGEST_DRY_RUN,
            Scope.GITHUB_READ,
            Scope.CRM_ACCOUNT_READ,
            Scope.CONTRACTS_READ,
            Scope.FINANCE_READ,
            Scope.PUBLISHING_READ,
            Scope.DISCORD_READ,
            Scope.AUDIT_READ,
        }
    ),
    RiskTier.R1: frozenset(
        {
            Scope.KNOWLEDGE_INGEST,
            Scope.MEMORY_WRITE_PERSONAL,
            Scope.AUDIT_APPEND,
        }
    ),
    RiskTier.R2: frozenset(
        {
            Scope.GITHUB_PR_CREATE,
            Scope.PUBLISHING_SEND,
            Scope.DISCORD_SEND,
            Scope.KNOWLEDGE_PROMOTE_CLAIM,
        }
    ),
    RiskTier.R3: frozenset(
        {
            Scope.CRM_OPPORTUNITY_UPDATE,
            Scope.CRM_BULK_EXPORT,
            Scope.ADMIN_PLATFORM,
            Scope.KNOWLEDGE_FORGET,
            Scope.GITHUB_PROTECTED_MERGE,  # high / R3 — matrix §3 Deploy, spec 36.1
            Scope.APPROVAL_DECIDE,
        }
    ),
    RiskTier.R4: frozenset(
        {
            Scope.CONTRACTS_SIGN,
            Scope.FINANCE_PAYMENT,
            Scope.IDENTITY_IMPERSONATE,
        }
    ),
}

# Scopes a service principal MUST NOT hold (spec 15.3–15.6).
EMPLOYEE_ONLY_SCOPES: frozenset[str] = frozenset(
    {
        Scope.IDENTITY_IMPERSONATE,
        Scope.MEMORY_WRITE_PERSONAL,
        Scope.APPROVAL_DECIDE,
        "user:employee-a/private",
        "user:employee-b/private",
        "user:employee-c/private",
        "user:employee-a/restricted",
        "user:employee-b/restricted",
        "user:employee-c/restricted",
        Scope.CONN_GITHUB_OAUTH_PREFIX,
    }
)

EMPLOYEE_PRIVATE_SCOPES: frozenset[str] = frozenset(
    {
        "user:employee-a/private",
        "user:employee-b/private",
        "user:employee-c/private",
        "user:employee-a/restricted",
        "user:employee-b/restricted",
        "user:employee-c/restricted",
    }
)


def is_employee_scope(scope: str) -> bool:
    if scope in EMPLOYEE_ONLY_SCOPES:
        return True
    if scope.startswith("user:"):
        return True
    if "github-oauth" in scope:
        return True
    return False


def owner_slug_from_user_scope(scope: str) -> str | None:
    """Parse `user:<slug>/private` or `user:<slug>/restricted`."""
    if not scope.startswith("user:"):
        return None
    rest = scope[len("user:") :]
    slug, _, _tail = rest.partition("/")
    return slug or None
