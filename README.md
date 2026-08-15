# Company Hermes Agent Platform (generic template)

This repository is the **generic company template** for the Hermes
company-agent platform. Fork it once per company. It contains **no**
live company context: names, emails, domains, and legal entities are
placeholders.

Normative spec: `spec/spec.md` (v1.1).

## What this is

A publishable starting tree:

- `spec/` — the generic zero-to-production spec
- `governance/` — role registry, classification, integrations, approval
  matrix, GitHub org controls, ADR template, decisions template
- `distribution/` — Hermes profile distribution (`SOUL.md`, `AGENTS.md`,
  config, skills, plugins, cron, policies, runbooks)
- `services/` — Phase 2–3 Python services (knowledge, approval, authz,
  connectors). Credential-free scaffold.
- `skills/onboarding/` — employee `USER.md` onboarding skill
- `infra/` — Compose + systemd unit templates
- `scripts/` — VPS bootstrap and Pi→VPS migrate helper
- `webui/` — login-protected profile chat (runtime users, not in git)

## Layout

```
company-agent-template/
  README.md
  LICENSE
  INSTALL.md
  .env.EXAMPLE
  spec/spec.md
  governance/
  distribution/
  services/
  skills/onboarding/
  webui/
  infra/
  scripts/
```

## Template → company fork

1. Create a private repo under `<GITHUB_ORG>` (D042).
2. Fork or clone this template. Rename the remote. Keep branch `main`.
3. Copy `governance/DECISIONS-NEEDED-template.md` to
   `governance/DECISIONS-NEEDED.md` and fill TODOs. Do not invent answers.
4. Replace placeholders:
   - `<Company>` / `<company>` — display name / slug
   - `<company-domain>` — email / web domain
   - `<Employee A>`, `<Employee B>`, `<Employee C>` — real names
   - `employee-a` / `employee-b` / `employee-c` — keep as slugs unless
     you change them everywhere (code, migrations, tests)
   - `automation` — non-human service profile (spec 15.3)
5. Fill `.env` from `.env.EXAMPLE` and `infra/.env.EXAMPLE`. Never commit
   real values.
6. Follow `INSTALL.md`.

## Install (short)

See `INSTALL.md` for the full path. Short version on Ubuntu 24.04:

```bash
sudo bash scripts/bootstrap.sh https://github.com/<GITHUB_ORG>/company-agent-template.git
```

Then create profiles:

```bash
hermes profile create automation --no-alias
hermes profile install /opt/company-agent/distribution --name automation -y
hermes profile create employee-a --no-alias --no-skills
```

## Tests

Offline services suite (no database, no network):

```bash
cd services
python3 -m pytest tests/ -x -q
```

## License

Proprietary template. See `LICENSE`. `<Copyright owner>` is a
placeholder until D052 closes.
