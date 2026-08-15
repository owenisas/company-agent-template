# Profiles (Phase 1b)

Normative sources: spec 11.3, 15.1–15.6, 16.4–16.5, 32.7.
Runtime state is **not** in this repository. Profiles live on the control-plane
host under `~/.hermes/profiles/<name>/` (the built-in `default` profile is
`~/.hermes` itself). Do not commit anything from those directories.

## The four company profiles

| Profile | Role | Kind | Tool-only | Credentials (Phase 1b) |
|---|---|---|---|---|
| `automation` | Non-human service principal for scheduled / event-triggered company work | Service | Yes (policy below) | `COMPANY_PROFILE_ID=automation` only. Other `env_requires` are documented placeholders. No OAuth, no personal tokens. |
| `employee-a` | Isolated individual employee profile (slug; name TODO D001) | Human | No | None. `USER.md` is `TODO: real name/email`. |
| `employee-b` | Isolated individual employee profile (slug; name TODO D002) | Human | No | None. `USER.md` is `TODO: real name/email`. |
| `employee-c` | Isolated individual employee profile (slug; name TODO D003) | Human | No | None. `USER.md` is `TODO: real name/email`. |

Legacy host profiles (whatever already exists on the machine) are out of
scope. They MUST remain isolated (D050). Phase 1b does not map them onto
`employee-*`.

Created on Hermes v0.20.1:

```bash
# Automation: spec 17 install flow, non-interactive
hermes profile install /path/to/company-agent-distribution \
  --name automation -y

# Employees: fresh isolated profiles, no clone (would copy .env / auth)
hermes profile create employee-a --no-alias --no-skills \
  --description "<Company> employee profile (slug employee-a)."
# same for employee-b / employee-c
```

Per-profile config (verified keys):

```bash
hermes -p <profile> config set model.provider <MODEL_PROVIDER>
hermes -p <profile> config set model.default <MODEL_ID>
hermes -p <profile> config set model.reasoning_effort <REASONING_EFFORT>
```

`automation` keeps the distribution `terminal.backend: docker`
(D053: docker is not installed; do not install it in this phase).

## Tool-only policy for `automation` (spec 15.6)

v0.20.1 has **no** first-class `tool_only` / `automation.tool_only` config
key (probed via `hermes config get`; see DECISIONS-NEEDED D054). Closest
supported controls, all applied on the automation profile only:

1. **Disable the execution-plane toolsets** so a run cannot open a host
   shell, in-process interpreter, or desktop computer-use session:
   `terminal`, `code_execution`, `computer_use`.
   - Official write path: `hermes -p automation tools disable <name>`
   - Layered denylist: `agent.disabled_toolsets` (a YAML list). Cron applies
     this denylist on top of its own interactive-tool denylist
     (`messaging`, `clarify`, `memory`, and `cronjob` unless
     `cron.allow_agent_scheduling` is true).
2. **Non-interactive invocation** for jobs: `hermes -p automation chat -q …`
   or `--oneshot`. There is no “disable the interactive loop” config key.
3. **Cron stays off** until Phase 2. Distribution `cron/*.yaml` files have
   `enabled: false`. `hermes profile install` copies them as catalog policy
   and does **not** schedule them (`cron/jobs.json` is absent).

`terminal.backend` remains `docker` as shipped (spec 16.6 / D053). That is
the sandbox setting for a future worker path, not permission to run a
shell today.

A code-executing job MUST be refused until an approved worker exists
(spec 15.6, 32.7). Phase 1b does not provision that worker.

## Invariant: automation never impersonates an employee (spec 15.6)

`automation` is a service identity, not a shared employee login.

- MUST NOT impersonate `employee-a/b/c` or any legacy personal profile.
- MUST NOT reuse an employee's Gmail, Slack, GitHub, CRM, or other
  personal OAuth token.
- MUST NOT send, publish, sign, pay, delete, deploy, or change privileges
  without the applicable row in the action-approval matrix.
- MUST NOT execute arbitrary task code on the control-plane host.
- MUST NOT use `MEMORY.md` as a system of record for customer, legal,
  finance, project, or research data.

When a scheduled workflow needs an employee-attributed action: automation
prepares the exact payload, requests approval from the accountable
employee, and the final connector uses the approved delegated or company
principal. Automation MUST NEVER silently substitute its identity for the
human.

See `../company-agent-platform/docs/governance/action-approval-matrix.md`
section 1 (identity substitution constraint) and section 3 (per-action
automation column).

## How cron authority maps to this profile

Catalog files in `cron/` are versioned schedule **policy**, not live
Hermes `jobs.json` entries. Each file names:

| Field | Meaning |
|---|---|
| `profile` | Always `automation`. Jobs run as this principal. |
| `enabled` | `false` until a Phase 2 authorization. |
| `authority` | The maximum data/action scope of that job (spec 15.6 table). |
| `approval_gate` | Extra gate on top of the action-approval matrix. |
| `external_write` | If true, the matrix R2+ send/publish rules apply. |

| Job file | Catalog authority |
|---|---|
| `knowledge-indexing.yaml` | Read/write knowledge index only |
| `research-monitor.yaml` | Read web and knowledge; no external write |
| `company-briefing.yaml` | Read approved systems |
| `crm-hygiene.yaml` | Read CRM; reversible task creation only |
| `renewal-risk.yaml` | Read CRM/usage/support |
| `backup-verification.yaml` | Backup metadata and restore-test target |
| `release-check.yaml` | Read Git/CI, create checks |
| `campaign-analytics.yaml` | Read analytics and campaign data |

Authority in YAML is **not** enforcement. Enforcement is the combination
of: this profile's tool denylist, per-connection allowlists, MCP tool
includes in `config.yaml`, the approval service, and the matrix. A cron
job cannot widen `agent.disabled_toolsets` (v0.20.1 scheduler layers the
profile denylist onto every cron-spawned agent).

Phase 2 MUST authorize each job (D046/D047) before flipping `enabled`
or writing `jobs.json`.

## Isolation test

```bash
./tests/profile-isolation.sh
```

Recorded output: `tests/PROFILE-ISOLATION-1b.txt`.
