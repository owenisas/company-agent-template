# Decisions needed (template)

**Company slug:** `<company>`
**Normative sources:** spec Sections 8, 9, 11.3, 12, 12.5, 15.7, 28.3, 29.6, 33.5, 34 Phase 0, 37, 38
**Purpose:** Every placeholder a human MUST answer before Phase 1 connects production data.
**Rule:** Do not invent answers. Closing an item requires a named human decision, recorded here as Done and patched into the cited governance file.

Fork this file to `DECISIONS-NEEDED.md` in the company repo. Leave every row `TODO` until a human decides.

---

## People and identity

| ID | Decision | Status |
|---|---|---|
| D001 | Legal / display name of `employee-a` (`<Employee A>`) | TODO |
| D002 | Legal / display name of `employee-b` (`<Employee B>`) | TODO |
| D003 | Legal / display name of `employee-c` (`<Employee C>`) | TODO |
| D004 | Company email for each employee | TODO |
| D005 | GitHub username for each employee | TODO |
| D019 | Company email domain (`<company-domain>`) | TODO |

## Approvers and authority

| ID | Decision | Status |
|---|---|---|
| D006 | Responsibilities: who is builder, owner, approver, viewer, and in which domain | TODO |
| D007 | Which two humans are GitHub organization owners (MUST NOT be all employees) | TODO |
| D008 | Membership of `agent-platform-admins` | TODO |
| D009 | Membership of `agent-builders` | TODO |
| D010 | Membership of `agent-users` | TODO |
| D011 | Named legal owner / counsel and `legal-approvers` | TODO |
| D012 | Named finance owner and second finance approver | TODO |
| D013 | Named people / HR owner | TODO |
| D014 | Named customer-data owner and bulk-export second approver | TODO |
| D015 | Named platform-ops owner and break-glass / recovery administrator(s) | TODO |
| D016 | Who MAY change data classification, including restricted → lower | TODO |
| D017 | Two named humans who approve stable releases (`<PERSON_1>`, `<PERSON_2>`) | TODO |
| D018 | Authorized signer identity (human, not automation) | TODO |

## Source systems and connectors

| ID | Decision | Status |
|---|---|---|
| D020 | `<CRM_NAME>` and which objects/fields are in scope | TODO |
| D021 | `<CONTRACT_REPOSITORY>`: where contracts live and who may access them | TODO |
| D022 | `<FINANCE_SYSTEM>` and read vs write objects | TODO |
| D023 | `<CHANNEL_LIST>` publishing channels | TODO |
| D024 | Which email, Slack/Teams, and social accounts the agent MAY access | TODO |
| D025 | Whether Notion is production knowledge, an interim CRM, both, or out of scope. Live Notion connect is blocked until this closes. | TODO |
| D026 | Whether existing outreach/email send paths are a publishing channel | TODO |
| D027 | Whether chat (Slack/Discord/Teams) is the approval UX, notification-only, or out of production scope | TODO |
| D028 | Owner of each messaging integration | TODO |
| D063 | Field allowlists for GitHub / CRM / Notion read-only tools until D020/D025/D042 name the real objects | TODO |

## Hosting, region, backups, secrets

| ID | Decision | Status |
|---|---|---|
| D029 | Control-plane host: private Ubuntu 24.04 VPS (spec 5.2 default) vs one-host equivalent (spec 5.5) | TODO |
| D030 | Knowledge data region and residency requirements | TODO |
| D031 | Execution worker: local only, isolated worker on the same host, second worker host, or managed ephemeral sandbox | TODO |
| D032 | Raw object storage: encrypted local filesystem vs S3-compatible (product + region) | TODO |
| D033 | Off-host encrypted backup target and key custody | TODO |
| D034 | Secrets provider product (managed vs MVP file/Docker secrets) | TODO |
| D035 | Company identity / VPN / MFA product for human auth to KB/MCP | TODO |
| D036 | Retention periods that differ from spec 8 / 31 defaults | TODO |
| D055 | How PostgreSQL + pgvector is hosted | TODO |
| D056 | Integer embedding width for `chunk_embeddings.embedding vector(N)` | TODO |
| D059 | Concrete raw-object root (`OBJECT_STORE_ROOT`) once D032 is closed | TODO |

## Models and research

| ID | Decision | Status |
|---|---|---|
| D037 | Approved primary model provider, model ids, data-retention terms, and billing | TODO |
| D038 | Approved fallback provider and the same terms | TODO |
| D039 | Whether any existing model proxy is an approved path | TODO |
| D040 | Embedding model, dimensions, and provider data terms | TODO |
| D041 | First Agency Agents specialist roles actually wanted | TODO |

## GitHub and release

| ID | Decision | Status |
|---|---|---|
| D042 | `<GITHUB_ORG>` name | TODO |
| D043 | CODEOWNERS replacements for `<LEGAL_OWNER>` and `<FINANCE_OWNER>` | TODO |
| D044 | Whether signed commits are mandatory | TODO |
| D045 | Required CI check names | TODO |
| D052 | Company legal name for distribution `author` and plugin manifests | TODO |
| D053 | Company sandbox image name and sha256 digest | TODO |

## Automation and credentials

| ID | Decision | Status |
|---|---|---|
| D046 | Which automation schedules launch first | TODO |
| D047 | Which service identities those schedules use | TODO |
| D048 | Which actions need service accounts instead of delegated user OAuth | TODO |
| D049 | Approval UX location: Hermes UI, Slack, email, chat, or internal dashboard | TODO |
| D050 | Mapping or retirement of any pre-existing Hermes profiles onto `employee-*` / `automation` | TODO |
| D051 | Owner of the GitHub machine/App integration | TODO |
| D054 | How `automation` is kept tool-only until a first-class Hermes mode exists | TODO |
| D057 | Whether services pin Python dependency versions or stay unpinned + lockfile | TODO |
| D058 | Alembic vs numbered `.sql` migrations | TODO |
| D060 | Approval request fingerprint algorithm | TODO |
| D061 | Default approval TTL | TODO |
| D062 | On-disk format for profile `connection-references/` | TODO |

---

## How to close an item

1. A human writes the answer (name, system, or explicit “out of scope”).
2. Patch the cited governance file in the same change.
3. Mark the row **Done** with the date.
4. Do not put secrets in the answer — record class, owner, and scope only (spec 12.2).

Phase 1 MUST NOT connect production CRM, contract, finance, HR, or customer systems while D011–D014 and D020–D025 remain open.
