# Installation guide

Definitive install for a fork of this template. Prerequisites through
day-one checks. Company-specific answers come from
`governance/DECISIONS-NEEDED-template.md` (copy to `DECISIONS-NEEDED.md`).

## Prerequisites

- Ubuntu Server 24.04 LTS (spec 6 baseline)
- Two company administrators on the cloud/VPS account
- Private network or identity path to the host (VPN / allowlisted SSH)
- GitHub org name chosen or still `TODO: <GITHUB_ORG>` (D042)
- Hermes Agent >= 0.20.1 available for profile install
- No production CRM / legal / finance / HR data connected while D011–D014
  and D020–D025 are open

Do not put secrets in Git, prompts, `SOUL.md`, `USER.md`, or skill files.

## VPS sizing

Spec §5.5 (one-host startup and split triggers) and §6.1 / §6.2
(suggested initial sizing). Section 33 is day/week/month operations,
not hardware sizing.

| Resource | Minimum start | Prefer when busy |
|---|---|---|
| CPU | 4 vCPU | 8 vCPU |
| RAM | 16 GB | 32 GB |
| Disk | Encrypted volume sized for DB + raw objects + Git + 2x backup | 3x active data |
| GPU | None on this VPS | Hosted model APIs only |

A three-person company MAY begin with one VPS for the control plane and
a logically isolated worker path, with arbitrary code execution disabled
until the worker boundary is tested. Split the worker when any of these
is true (spec 5.5):

- browser automation or untrusted code becomes routine
- builds or ingestion cause DB latency or memory pressure
- more than two long-running jobs must run concurrently
- a workflow needs a different network or credential access
- legal / finance / customer / production data needs a separate blast radius
- jobs must survive control-plane maintenance
- RAM or CPU stays above 60% during normal operation

## Clone

```bash
sudo mkdir -p /opt/company-agent
sudo git clone https://github.com/<GITHUB_ORG>/<REPO>.git /opt/company-agent
cd /opt/company-agent
```

Or run `scripts/bootstrap.sh` with the clone URL (idempotent).

## Environment

```bash
cp .env.EXAMPLE .env
cp infra/.env.EXAMPLE infra/.env
chmod 600 .env infra/.env
```

Replace every `<PLACEHOLDER>`. Shared service credentials go in the
deployment secret system (D034), not in a profile `.env`.

Per-profile env (after `hermes profile create`):

```text
COMPANY_PROFILE_ID=<IMMUTABLE_PROFILE_ID>
COMPANY_USER_ID=<IMMUTABLE_USER_ID>
COMPANY_KB_MCP_URL=https://agent-services.<PRIVATE_DOMAIN>/mcp/knowledge
COMPANY_KB_TOKEN=<PER_USER_OR_SHORT_LIVED_TOKEN>
COMPANY_APPROVAL_URL=https://agent-services.<PRIVATE_DOMAIN>/approvals
COMPANY_APPROVAL_TOKEN=<PER_USER_OR_SHORT_LIVED_TOKEN>
```

## Docker Compose up

From `infra/`:

```bash
docker compose --env-file .env up -d
docker compose ps
```

Services in `infra/compose.yaml` (images and published ports are
placeholders or commented until D053 / D055 close):

- postgres + pgvector
- knowledge-api
- knowledge-worker
- knowledge-mcp
- approval-api
- audit-consumer
- webui (reserved)

Do not apply SQL migrations until D055 / D056 / D040 close.

## Profile creation

```bash
# Non-human service profile (spec 15.3). Never copy an employee profile.
hermes profile create automation --no-alias --no-skills \
  --description "<Company> automation service principal"
hermes profile install /opt/company-agent/distribution --name automation -y

# Isolated employees. Do not clone (clone would copy .env / auth).
hermes profile create employee-a --no-alias --no-skills \
  --description "<Company> employee profile (slug employee-a)"
hermes profile create employee-b --no-alias --no-skills
hermes profile create employee-c --no-alias --no-skills
```

Install the distribution into each employee profile only after reviewing
`distribution/config.yaml`. Set model keys from D037:

```bash
hermes -p employee-a config set model.provider <MODEL_PROVIDER>
hermes -p employee-a config set model.default <MODEL_ID>
```

Copy `skills/onboarding/` into the profile skills directory when
onboarding a person. Load the onboarding skill and follow its procedure
before writing `memories/USER.md`.

## WebUI login bootstrap

See `webui/README.md`. Short path:

```bash
cd /opt/company-agent/webui
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
install -m 600 /dev/null runtime/users.json
.venv/bin/python -m backend.passwd '<admin>' \
  --role admin --profile default --write
./install-webui-service.sh
systemctl --user start hermes-webui.service
```

Record the first owner in the user-role registry. Rotate the bootstrap
password. Do not commit `runtime/users.json`. D035 (company identity +
MFA) remains open; this local username/password gate is the Phase-1
host login, not the long-term IdP.

## First-run checks

- [ ] `docker compose ps` shows only the services you intended to start
- [ ] `python3 -m pytest services/tests/ -q` is green
- [ ] `hermes -p automation config get` points at the automation profile
- [ ] employee profile directories are distinct and not writable by
      `automation`
- [ ] no real token appears in `git grep` or profile `.env` that was
      committed
- [ ] knowledge-api / approval-api return `not_configured` rather than
      pretending to persist
- [ ] kill-switch runbook is readable (`distribution/runbooks/incident-kill-switch.md`)

## Day-one checklist mapping

| Day-one item | Spec | Where |
|---|---|---|
| Two admins on the VPS account | 5.2, 33 | cloud console |
| Encrypted disk | 10 | host |
| Private DNS / SSH path | 10 | host |
| `DECISIONS-NEEDED.md` forked and open | 8, 37 | `governance/` |
| Employee slugs bound | 11.3 | user-role registry |
| `automation` profile exists and is not a copy | 15.3–15.5 | Hermes profiles |
| Distribution installed | 16, 17 | `distribution/` |
| Compose stack up or explicitly deferred | 13, 14 | `infra/` |
| Backups scheduled or explicitly TODO | 31, 33.1 | D033 |
| Daily operator checks understood | 33.1 | spec §33.1 |
| Departure runbook exists | 33.5 | `distribution/runbooks/user-departure.md` |
| New-integration procedure exists | 33.6 | integration inventory |
| No production connector live | 34 Phase 0 | D020–D025 |

## Moving a Pi one-host install to this VPS

See `scripts/migrate-from-pi.sh`. Generic rsync of profiles, env, and
data dirs. Review D050 before mapping legacy profiles onto `employee-*`.
