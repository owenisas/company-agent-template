# Integration inventory and owners

**Company slug:** `<company>`
**Normative sources:** spec Sections 2, 4.2, 8, 12.1–12.4, 15.4, 29.5, 29.6, 33.6, 34 Phase 0, 37, Appendix B
**Status:** Phase 0 baseline
**Owner of this inventory:** TODO: platform-ops owner
**Review cadence:** On every new integration (spec 33.6) and during weekly operator checks once live

This inventory lists every integration the spec requires for the three-person baseline, plus control-plane services the fork actually runs. It records owner, credential class (spec 12.1), scope, purpose, and status. It MUST NOT contain secrets, tokens, PEMs, or connection strings. Credentials are referenced by class, owner, and scope only.

A shared credential without an owner and purpose MUST NOT be issued (spec 34 Phase 0). Rows marked `TODO:` are not authorized for production use.

## 1. Credential classes (spec 12.1)

| Class | External actor | Default use on this platform |
|---|---|---|
| Personal | Human employee (`employee-a` / `b` / `c`) | User-initiated work and attributable communication |
| Shared service | Company service principal (`automation` or a named bot) | Repeatable company automation |
| Delegated / assumed | Company service acting for an employee after approval | High-control systems that support delegation |

Shared service credentials MUST belong to a non-human principal, use least scopes, remain unavailable through terminal or generic HTTP tools, emit requester and service-principal attribution, and support rotation and revocation (spec 29.5, 12.3). High-risk credentials (payments, signing, production privilege changes, destructive actions) MUST be brokered and MUST NOT be exposed to Hermes (spec 12.4).

## 2. Required integrations

Status values: `planned` (spec baseline, not built), `present-ungoverned` (exists on the host today outside this policy), `blocked-unknown-scope` (must not connect until TODOs close), `not-selected`.

| Integration | Connection ID (illustrative) | Owner | Credential class | Scope | Purpose | Allowed action posture | Rotation | Status |
|---|---|---|---|---|---|---|---|---|
| GitHub | `company/github-hermes-bot` | TODO: engineering owner | Shared service | Company repos listed in `github-org-controls.md` | PR creation, issue comments, read for CI/eval | Read + PR/issue write. MUST NOT delete repos or modify branch protection (Appendix B pattern) | 90d or GitHub App installation-token lifetime | present-ungoverned on Pi (machine auth exists); production policy not yet applied |
| GitHub (personal) | `user:<slug>/github-oauth` | The employee | Personal | That user | User-authorized repository work | Provider-scoped to the human | Provider | planned; three employees TODO: GitHub handles |
| CRM | `company/crm-readonly` | TODO: RevOps / CRM owner | Shared service | Revenue / CS objects TODO: | Read accounts/contacts/opportunities | Read-only until write runbooks exist | 90d | blocked-unknown-scope — TODO: `<CRM_NAME>` |
| CRM writes | `team:revenue/crm-automation` | TODO: RevOps / CRM owner | Shared service or delegated | Revenue | Approved field updates only | Preview/apply + approval (spec 12.5 R2/R3) | 90d | blocked-unknown-scope |
| Contract repository | `company/contracts` | TODO: legal owner | Shared service (read) / brokered (sign) | Legal matters | Retrieve authorized matter documents | Read within matter ACL. Sign is R4 brokered. | 90d | blocked-unknown-scope — TODO: `<CONTRACT_REPOSITORY>` |
| Finance system | `company/finance-readonly` | TODO: finance owner | Shared service (read) / brokered (pay) | Finance | Bookkeeping prep, AP draft, reporting | Read-only in Hermes. Payment is R4 brokered (spec 12.4, 29.6). | 90d | blocked-unknown-scope — TODO: `<FINANCE_SYSTEM>` |
| Publishing channels | `company/email-platform`, `company/social-brand` | TODO: marketing / publishing owner | Shared service | Marketing | Approved campaigns and brand posts | R2/R3 explicit approval. Autonomous external sends disabled at launch (spec 8). | 90d | blocked-unknown-scope — TODO: `<CHANNEL_LIST>` |
| Knowledge service | `company/knowledge-api` | TODO: platform-ops owner | Shared service (API) + user JWT (humans) | Company knowledge per ACL | Ingest, search, cite, restrict, delete-propagate | Users: short-lived JWT. Automation: service token (spec 8). | 90d / token TTL | planned (Phase 2) |
| PostgreSQL / pgvector | `company/postgres` | TODO: platform-ops owner | Shared service | Control-plane data stores | Knowledge, ACL, audit metadata | App roles only. Agent shell MUST NOT receive the admin URI (spec 5.2, 12.2). | 90d | planned (Phase 2). MUST NOT share the worker network. |
| Object storage (raw evidence) | `company/raw-objects` | TODO: platform-ops owner | Shared service | Encrypted evidence bucket/volume | Store raw objects separately from derived chunks (spec 38.8) | Server-side write from ingestion workers only | 90d | planned — TODO: encrypted local volume vs S3-compatible |
| MCP services (platform) | `company/knowledge-mcp`, `company/approval-mcp` | TODO: platform-ops owner | Shared service | Control plane | Typed tools; server-side secret use | Minimal schemas, tool allowlists, output filtering (spec 5.7) | 90d | planned |
| MCP services (connectors) | `company/github-mcp`, `company/crm-mcp`, others | Integration owner in this table | Shared service or personal ref | Declared tenant/resources | Narrow typed tools per spec 33.6 | No raw secret in tool results | 90d | planned / blocked per row |
| Chat gateway | `company/chat-gateway` | TODO: communications owner | Shared service (bot) + Personal (human chat accounts are out of bot scope) | Company workspace / approved channels | Team messaging and operator notifications | Channel allowlist. Secrets MUST stay in DMs, never echoed to channels. MUST NOT be an approval system of record unless chosen in TODO: approval UX. | 90d | not-selected — TODO: D027 / D028 |
| Approval service | `company/approval-api` | TODO: platform-ops owner | Shared service | Company | Time-bound, action-specific approvals (spec 12.5) | Named / two-person as required by the matrix. Automation MUST NOT self-approve consequential actions. | 90d | planned (Phase 3) |

## 3. Control-plane adjacent services (inventory only)

These are inventoried so production scope is not implicit. They are not automatically in-scope sources of truth.

| Integration | Owner | Credential class | Scope | Purpose | Status |
|---|---|---|---|---|---|
| Hermes runtime (existing host profiles) | TODO: platform-ops owner | Personal (those profiles) | Local control-plane host | Interactive use before `employee-*` and `automation` exist | planned — TODO: map or retire profiles (D050) |
| Model proxy (if any) | TODO: platform-ops owner | Shared service | Control plane → model broker | Model access for Hermes | not-selected — TODO: confirm as approved model path (D037 / D039) |
| Notion workspace / MCP | TODO: knowledge or CRM owner | Shared service or personal OAuth | TODO: workspace scope | Docs/tasks; MUST NOT be assumed to be `<CRM_NAME>` or the contract repository | not-selected — TODO: D025 |
| Hosted email send path (if used) | TODO: publishing / revenue owner | Shared service | TODO: from-addresses and audiences | External send is R2 and disabled for autonomous launch (spec 8) | not-selected — TODO: D026 |
| Object / wiki files on the control-plane host | TODO: platform-ops owner | N/A (host files, not a connector) | Host filesystem | Agent-compiled notes. MUST NOT be treated as governed knowledge until ingested under ACL. | planned |

No credential material is recorded for these rows. Existing secret locations MUST be migrated to the approved secrets provider (spec 12.2) before they are treated as production shared credentials. Secrets provider product: TODO.

## 4. Shared-credential owner and purpose checklist

Every shared (non-personal) row above MUST have all of the following before issue or reuse (spec 12.2, 34 Phase 0):

```text
secret_id / connection id
owner
system
principal (non-human)
scopes
rotation_interval_days
break_glass_owner
purpose (business object + why a service account is required vs delegated user OAuth)
```

Current state: owners and several systems are `TODO:`. Therefore **no new production shared credential may be created from this inventory**, and present-ungoverned credentials MUST be treated as undocumented risk until bound to a named owner.

## 5. New integration procedure (spec 33.6)

Operators MUST:

1. identify owner and business purpose;
2. classify data and actions (`docs/governance/data-classification-retention.md`);
3. choose personal / shared / delegated connection;
4. define least scopes;
5. implement narrow typed MCP tools;
6. add preview/apply and approvals;
7. add redaction and audit;
8. create a staging tenant or test account;
9. write authorization and injection tests;
10. release `working` → `testing` → `stable` (spec 5.8);
11. set rotation and offboarding;
12. add a row to this file in the same pull request that introduces the connector.

## 6. Explicit non-inventory

The following MUST NOT appear as undocumented side channels:

- employee personal Gmail/Slack/GitHub tokens reused by `automation` (spec 15.3);
- high-risk payment or signing keys in any Hermes environment file (spec 12.4);
- GitHub PATs in clone URLs, scripts, `.env.EXAMPLE`, or chat (spec 9.4);
- Discord channel messages used as a secret store.
