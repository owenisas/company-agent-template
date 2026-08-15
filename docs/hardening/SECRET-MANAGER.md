# Dedicated secret manager

Phase 5 §4510. Product choice still open (**D034**). Goal: no long-
lived production secret in git, Hermes context, or world-readable
unit files.

## Secrets that exist today (inventory)

These live on the appliance / planned VPS. **Values are not recorded
here.**

| Secret | Typical location today | Class | Notes |
|---|---|---|---|
| Model-provider OAuth / API key | Hermes provider config / user keyring | Company inference | D037/D038; do not copy into distributions |
| Notion PAT | `notion-pat.env` or MCP token dir (mode 0600) | Shared or personal connector | Prefer OAuth; PAT is interim (docs/notion-setup.md) |
| Notion OAuth client secret | `.env` (not committed) | App secret | `.env.EXAMPLE` has placeholders only |
| Dashboard auth / session secret | Hermes `config.yaml` / unit Environment | Platform | Rotate on suspected exposure |
| Dashboard user password hashes | `~/.hermes/dashboard-users.json` (0600) | Identity | scp out of band; never git |
| Postgres password | `infra/vps/.env` | Data store | Compose `${POSTGRES_PASSWORD}` |
| Embedding API key | `infra/vps/.env` | Inference | D040 |
| GitHub App PEM / deploy key | `~/.hermes/secrets/` (0600) | SCM | Machine identity; not a human PAT |
| Approval / KB per-user tokens | runtime | Short-lived | Prefer brokered |

Shared service credentials MUST NOT enter Hermes terminal or profile
MEMORY (spec 12.2, 16.2).

## Target design

MVP (recommended until D034 names a product):

1. **systemd EnvironmentFile** (mode 0600, root or service user)
   for unit-scoped values (`hermes-serve`, `hermes-desktop-web`).
2. **SOPS + age** for encrypted-at-rest copies of `.env` and
   `notion-pat.env` in an operators-only store (not this git repo).
   Age recipients = named platform admins (D008/D015).
3. Compose reads `.env` on the VPS only (`chmod 600`).

Later:

- Vault / cloud secret manager if the company already runs one.
- Credential broker for signing/payment (spec 12.4) — those secrets
  MUST NEVER be in EnvironmentFile.

## Move procedure

1. Inventory every file matching `*token*`, `*.pem`, `.env`,
   `dashboard-users.json`, `mcp-tokens/`.
2. Encrypt with SOPS; delete plaintext from shared disks after the
   first restore test.
3. Point units at `EnvironmentFile=-/etc/company-agent/hermes.env`.
4. Confirm `git log -S` / `gitleaks` on this repo is clean (already
   required for Phase 0).
5. Revoke any secret that ever sat in a ticket or chat.

## Rotation cadence

| Class | Cadence |
|---|---|
| Human dashboard password | 90 days or on departure (spec 33.5) |
| Notion PAT / OAuth client secret | 90 days |
| Model provider key | 90 days or on provider incident |
| Postgres password | 90 days + after restore-to-new-host |
| GitHub App install tokens | Hourly by design; PEM on compromise only |
| Age / SOPS recipients | When an admin leaves |

## Access control

- Read: `agent-platform-admins` only (D008).
- Break-glass: D015 recovery admin, two-person for production
  payment/signing (those stay in the broker, not here).
- `company-automation` gets short-lived scoped tokens, never the
  SOPS age key.
- Audit: who decrypted what (SOPS key use / Vault lease).
