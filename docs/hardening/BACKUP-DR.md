# Backup and disaster recovery

Phase 5 §4514. Spec 31.1–31.4. Off-host target is **TODO D033**.
A backup that has not been restored is unproven.

## What is backed up

| Asset | Source on VPS / Pi | Script path |
|---|---|---|
| Hermes profiles | `${HERMES_HOME:-$HOME/.hermes}/profiles` | `profiles/` |
| Dashboard users | `${HERMES_HOME}/dashboard-users.json` | `config/` |
| Notion PAT env | `${NOTION_PAT_ENV:-$HOME/.hermes/secrets/notion-pat.env}` | `config/` |
| Company repos | `${COMPANY_REPOS_DIR:-$HOME/workspace}` | `repos/` |
| PostgreSQL | `docker compose exec postgres pg_dump` | `postgres/` |
| Release manifests | `distribution/manifests/` inside the repo bundle | `repos/` |
| Audit export (when present) | compose volume / API export | `audit/` |

Git remotes are **not** a backup of profile state, raw notes, or
databases (spec 31.1).

## Schedule (spec 31.2)

| Asset | Frequency | Retention |
|---|---|---|
| PostgreSQL logical dump | Daily + WAL/snapshot if available | 30 daily, 12 monthly |
| Profiles + dashboard users + PAT env | Daily, snapshot-consistent | 30 daily |
| Repo mirror bundles | Daily | 90 days |
| Release manifests | Every release | Indefinite |
| Audit store | Daily | ≥ 1 year |

## Off-host target

```text
TODO D033: off-host encrypted backup target and key custody.
```

`scripts/hardening/backup.sh` encrypts locally (age, if
`BACKUP_AGE_RECIPIENT` is set) and copies to `BACKUP_OFFHOST`
when that variable is set. If it is unset the script **fails
closed** after writing the local bundle — local-only is not DR.

## Restore drill (quarterly, spec 31.4)

1. Provision an isolated test host or VM. Do not restore onto
   production volumes.
2. Decrypt the newest off-host bundle (D033 key).
3. Restore Postgres to a throwaway instance. Check schema + row
   counts.
4. Verify random raw-object / dump hashes against `SHA256SUMS`.
5. Start knowledge-api against the restored DB; run ACL tests.
6. Restore one profile; confirm that user's memory is present and
   another user's is not.
7. Confirm stable release manifest hashes.
8. Record wall-clock RTO and data-gap RPO. Keep the previous
   production backup intact.

## RTO / RPO notes

| Scenario | Target RPO | Target RTO | Blocker |
|---|---|---|---|
| Single service crash | 0 (volumes) | < 30 min | None |
| VPS disk loss | Last successful off-host dump (≤ 24h once D033 closes) | < 8 h | **D033** |
| Region / provider loss | Same | < 24 h | D033 + second admin (D015) |
| Accidental restricted delete | Point-in-time before delete, unless legal hold | Domain owner | Legal hold overrides (RETENTION.md) |

These numbers are planning targets, not a contract.

## Script

```bash
BACKUP_OFFHOST=  # TODO D033
BACKUP_AGE_RECIPIENT=  # age public key
sudo -u hermes bash scripts/hardening/backup.sh
```

Cron sketch: `distribution/cron/backup-verification.yaml` (disabled
until D033).
