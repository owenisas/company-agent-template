# Data classification and retention policy

**Company slug:** `<company>`
**Normative sources:** spec Sections 2, 4.2, 4.3, 8, 12.2, 28.1, 28.3, 29.1, 29.6, 31.1–31.5, 34 Phase 0, 37
**Status:** Phase 0 baseline
**Owner of this policy:** TODO: platform-ops owner jointly with TODO: legal owner
**Review cadence:** At least quarterly, and whenever a new integration or restricted domain is added (spec 33.6)

This policy defines classification levels, retention, deletion propagation, and who MAY change classification. Production installation MUST NOT begin while the data scope of a connected system is unknown (spec 34 Phase 0). Unknown retention or residency answers remain `TODO:` and are listed in `DECISIONS-NEEDED.md`.

## 1. Classification levels

Sensitivity vocabulary is the controlled taxonomy in spec 28.1. <Company> MUST use these four levels and MUST NOT invent additional top-level classes until usage data shows the need.

| Level | Meaning | Typical examples | Default Hermes / connector handling | Maps to |
|---|---|---|---|---|
| `public` | Intended for unrestricted external disclosure after approval of the claim, not merely because it appeared on the public internet | Approved marketing pages, published brand guidance, public product facts | MAY be retrieved broadly after promotion (spec 28.3). Social posts remain leads/evidence, not automatic facts (spec 38.10). | Spec 28.1 sensitivity `public` |
| `internal` | Company-ordinary information that would not be published but is not legally or financially privileged | Internal runbooks, engineering notes, non-restricted project decisions | Default for company-scope knowledge. Available to authorized employees within ACL. | Spec 28.1 `internal`; spec 29.1 company-confidential baseline when labeled up |
| `confidential` | Business-sensitive information whose unauthorized disclosure harms customers, employees, or the company | CRM accounts, unpublished pricing, customer success notes, unpublished research packets | MUST be ACL-scoped. MUST NOT enter another user's private profile memory. Shared credentials that can read this class MUST follow spec 12.3 and 29.5. | Spec 28.1 `confidential`; spec 29.1 |
| `restricted` | Legal, finance, HR/people, or customer data that spec 29.6 isolates, plus signing, payment, and production-admin material | Contracts and matters, invoices and bank details, employee records, bulk customer exports, signing/payment credentials | MUST use matter/account/tenant scoping, named approvers, and credential-broker patterns. MUST NOT be embedded into general company search. General agents MUST NOT sign or waive rights. | Spec 28.1 `restricted`; spec 29.6 domains |

Classification is independent of knowledge state (`candidate`, `verified`, `disputed`, `superseded`, `rejected`) and temporal type (spec 28.1). A `restricted` source that is `rejected` remains `restricted`.

## 2. Domain overlays (spec 29.6)

Restricted domains add controls on top of the `restricted` label. They do not replace it.

| Domain | Additional MUST | Named approver group | Human membership |
|---|---|---|---|
| Legal | Matter-level access; preserve original and executed document hashes; no cross-matter retrieval by default; privilege labels; qualified counsel review for high-risk or jurisdiction-specific work | `legal-approvers` | TODO: named legal owner / counsel |
| Finance | Separation of preparation and approval; no reusable payment credential in Hermes; exact amount/vendor/account in approval; duplicate-invoice and change-of-bank checks; two-person control for payment or bank-detail changes | `finance-approvers` | TODO: named finance owner |
| HR / people | Separate service/network and ACLs; avoid embeddings of highly sensitive fields unless required and protected; no general company search over employee records | `people-hr-approvers` | TODO: named people/HR owner |
| Customer data | Account/tenant scoping; purpose limitation; field redaction; no training or cross-customer memory without approved process; bulk export approval and expiration | `customer-data-approvers` | TODO: named customer-data owner |

Until those humans are named, the domain is **in scope as a prohibition**: connectors that would ingest that domain MUST remain disconnected from production (spec 34 Phase 0).

## 3. Who MAY change classification

| Change | Who MAY request | Who MUST approve | Who MUST NOT approve alone |
|---|---|---|---|
| `public` ↔ `internal` | Resource owner or builder | Resource owner | `automation` |
| `internal` → `confidential` | Resource owner or builder | Resource owner | Automation; a viewer |
| `confidential` → `restricted` | Resource owner | Domain approver for the target restricted domain (spec 28.3, 29.6) | The requester as sole approver when they are also the only domain owner, unless a written two-person exception exists |
| `restricted` → any lower class | Domain owner | Domain approver **and** TODO: legal owner when the record is legal, customer, or people data | Automation; any builder acting from retrieved content |
| Bulk reclassification | Platform owner | Domain approvers for every affected restricted class, plus a recorded purpose | Anyone using a shared service credential from a general shell |

Promotion of knowledge (spec 28.3) is not the same as classification change, but it MUST NOT lower sensitivity:

| Knowledge type | Who may promote (spec 28.3) |
|---|---|
| Personal preference | The user |
| Project fact/decision | Project owner or assigned team member |
| Company policy | Policy owner and required approver |
| Legal position | Authorized legal owner/counsel (TODO:) |
| Financial rule | Finance owner (TODO:) |
| Product specification | Product/engineering owner (TODO:) |
| Public company claim | Marketing/business owner plus applicable review (TODO:) |

Contradiction handling MUST link prior claims rather than erase them (spec 28.4). Deletion is a separate, authorized action (Section 5).

## 4. Retention

Spec 8 recommended defaults are adopted until TODO retention answers replace them. Audit retention MUST be at least one year unless legal/compliance requires longer (spec 8). Git is not a backup for uncommitted profile state, raw notes, or databases (spec 31.1).

### 4.1 Retention by classification

| Class / record type | Working / derived copies | Authoritative store | Backup overlay | Legal hold |
|---|---|---|---|---|
| `public` promoted claims | Until superseded | Curated knowledge repo / knowledge service | Release manifests kept indefinitely (spec 31.2) | N/A unless mistakenly classified |
| `internal` notes and project facts | Until owner deletes or project ends + TODO: project tail period | Knowledge service + source system | PostgreSQL backup schedule in 4.2 | Owner or legal MAY place hold |
| `confidential` business records | TODO: confirm vs source-system retention | Source system of record (CRM, etc. — TODO: names) | Encrypted backups; access restricted | TODO: legal owner |
| `restricted` legal | TODO: matter retention / jurisdiction | TODO: `<CONTRACT_REPOSITORY>` | Encrypted; legal-approver access only | Legal hold overrides ordinary deletion (spec 31.5) |
| `restricted` finance | TODO: statutory accounting retention | TODO: `<FINANCE_SYSTEM>` | Encrypted; finance-approver access only | Legal/finance hold |
| `restricted` HR/people | TODO: employment-aligned retention (spec 29.6) | TODO: HR system or none connected | Separate ACL; no general search | People/HR + legal hold |
| `restricted` customer | TODO: customer/contractual retention and residency | TODO: CRM / product systems | Tenant-scoped restore tests | Customer-data + legal hold |
| Personal Hermes memory | Pilot: write requires approval (spec 8). Retain until user departure + archive date (spec 33.5) | Profile volume, not the knowledge service | Encrypted profile backup, 30 daily (spec 31.2) | Only if legal hold named |
| Audit / traces | N/A | Audit store | Separate restricted backup daily (spec 31.2) | MUST be retained ≥ 1 year (spec 8) |
| Raw evidence objects | Separable from derived chunks (spec 38.8) | Encrypted object store (TODO: local volume vs S3-compatible) | Daily versioned encrypted sync; policy-dependent retention (spec 31.2) | Hold prevents expiry |

Data residency: TODO: confirm whether customer or legal location requirements exist (spec 37). Until answered, knowledge and backups MUST remain on the approved control-plane host and any explicitly approved off-host backup target, and MUST NOT be copied to an unapproved region.

### 4.2 Infrastructure backup schedule (spec 31.2)

Adopted as the initial operational target. This is not authorization to connect production data.

| Asset | Method | Frequency | Retention |
|---|---|---|---|
| PostgreSQL | Nightly logical dump + continuous/WAL or host snapshot where available | Daily + continuous | 30 daily, 12 monthly |
| Raw evidence | Versioned encrypted sync/snapshot | Daily | Policy-dependent (Section 4.1) |
| Hermes profiles | Encrypted file-level backup while gateway is stopped or snapshot-consistent | Daily | 30 daily |
| Git / repos | Remote + nightly mirror bundle | Daily | 90 days |
| Release manifests | Immutable copy | Every release | Indefinite |
| Audit store | Separate restricted backup | Daily | ≥ 1 year, then policy-dependent |

A backup that has not been restored is unproven (spec 31.4). Restore tests SHOULD run at least quarterly before production data is stored.

## 5. Deletion and restriction propagation (spec 31.5)

When an authorized deletion or restriction occurs, the platform MUST propagate as follows:

```text
source status        -> deleted / tombstoned
raw object           -> deleted, or retained only under legal hold
chunks               -> removed / inaccessible
embeddings           -> removed
summaries / claims   -> removed, rejected, or re-linked as policy requires
search caches        -> invalidated
research outputs     -> mark source unavailable; preserve audit lineage
backups              -> expire according to backup retention, not silently rewritten
```

Legal hold overrides ordinary deletion and MUST be visible to authorized administrators (spec 31.5). `automation` MAY execute an already-approved deletion runbook; it MUST NOT decide to delete restricted records.

Secrets MUST NOT be retained in Git, distributions, `SOUL.md` / `AGENTS.md` / `USER.md` / `MEMORY.md`, skills, notes, tool-call arguments when a reference can be resolved, general audit logs, images, or CI output (spec 12.2). Revocation on departure or suspected exposure is mandatory (spec 12.3, 33.5).

## 6. Unknown data scope control

The following scopes are **unknown** until `DECISIONS-NEEDED.md` is answered. Phase 1 MAY build isolated runtime with synthetic or redacted data (spec 5.8 `working`). Phase 1 MUST NOT connect production customer, legal, finance, or HR sources while these remain open:

- TODO: CRM objects and fields in scope
- TODO: contract repository contents and matter ACLs
- TODO: finance system read versus write objects
- TODO: publishing channel identities and audience lists
- TODO: knowledge retention exceptions vs this policy
- TODO: data residency / region
- TODO: whether existing Pi stores (Discord, Notion, outreach mail, local wiki) are in-scope production records or out-of-scope legacy

No production installation begins with unknown data scope: if a connector's class, owner, objects, and retention cannot be stated, it MUST stay disconnected.
