# Automated retention

Phase 5 §4513. Normative policy:
`governance/data-classification-retention.md` and spec 30.4 / 31.5.
This file is the **operator view** of what runs. It does not replace
the policy.

## What runs (scaffold)

No deletion job is enabled in production while D020–D024 / D036 are
open. The planned jobs:

| Job | Cadence | Acts on | Source of periods |
|---|---|---|---|
| `retention-debug-logs` | Daily | App / gateway debug logs | 14–30 days (spec 30.4) |
| `retention-model-io` | Daily | Full model input/output captures | 30–90 days unless approved longer |
| `retention-profile-cache` | Weekly | Ephemeral Hermes caches (not MEMORY.md) | 14 days |
| `retention-git-mirrors` | Weekly | Local repo bundles | 90 days (spec 31.2) |
| `retention-postgres-dumps` | Daily | Local dump directory | 30 daily / 12 monthly |
| `retention-audit-trim` | Monthly | Audit store past policy floor | ≥ 1 year; then D036 |
| `deletion-propagate` | On approved delete event | source, chunks, embeddings, caches | Policy §5 |

Implementation TODO: systemd timers or `company-automation` cron
entries, each with a dry-run flag. Do not wire them to production
data until the domain owners exist (D011–D014).

## Cadence vs classification

See policy §4.1. Summary:

- `public` promoted claims — until superseded
- `internal` — owner delete or project end + TODO tail (D036)
- `confidential` — source-system retention (D020 names)
- `restricted` legal / finance / HR / customer — statutory /
  matter / employment / contract periods (all TODO D036)
- Personal Hermes memory — until departure archive date
- Audit / traces — ≥ 1 year

## Legal-hold override

Legal hold **overrides ordinary deletion** (spec 31.5, policy §5).

Rules:

1. A hold is a named record: holder (legal owner — TODO D011),
   scope (source ids / matter / account), start, review date.
2. `deletion-propagate` MUST skip objects on hold and leave them
   visible to authorized admins.
3. Backups expire on their own schedule; they are not silently
   rewritten to erase a held object.
4. `company-automation` MAY execute an already-approved deletion
   runbook. It MUST NOT decide to delete restricted records or
   lift a hold.
5. Lifting a hold is a classification / privilege change (R3) and
   needs the legal owner.

## Operator check

Monthly (spec 33.3): confirm a restore point still exists, inspect
object-store and DB growth, and sample that a held fixture was not
expired.
