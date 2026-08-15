# <Company> company Hermes distribution

Proprietary — internal use. Spec: company Hermes agent platform v1.1,
Sections 16–21. Company slug `<company>`. Hermes requires `>=0.20.1`.

This repository is the versioned employee/automation profile distribution.
Live profile state is **not** stored here. Phase 1b created the four
company profiles on the control-plane host; see `docs/profiles.md`.

Author: `TODO: <COMPANY_LEGAL_NAME>` (DECISIONS-NEEDED D052).
GitHub org: `TODO: <GITHUB_ORG>` (D042).
CRM: `TODO: <CRM_NAME>` (D020).
Sandbox image: `TODO: <COMPANY_SANDBOX_IMAGE>@sha256:<DIGEST>` (D053).

## What is owned by the distribution

See `distribution.yaml`. MCP servers live in `config.yaml` (`mcp_servers`).
v0.20.1 does not use a separate `mcp.json` as the config format, so that
file is omitted (spec 16.2).

Instruction files `SOUL.md` and `AGENTS.md` are required at the profile
root (spec 16.4 / 16.5). Their text is authored in `docs/soul-baseline.md`
and `docs/agents-baseline.md`. Copy them to the repo root with
`scripts/materialize-instruction-files.sh` if a protected-file gate
blocked writing those names during authoring.

## Install (spec 17)

Do this on an employee workstation after private-repo access exists. Not
on this control-plane host during Phase 1a.

1. Confirm access (spec 17.1):

```bash
ssh -T git@github.com
git ls-remote git@github.com:<GITHUB_ORG>/company-agent-distribution.git
```

2. Install (spec 17.2):

```bash
hermes profile install \
  git@github.com:<GITHUB_ORG>/company-agent-distribution.git \
  --alias
hermes profile
# or: hermes -p <company> doctor
```

3. Private env (spec 17.3). Copy `.env.EXAMPLE` to the profile `.env`
   (mode 0600). Per-user values only. No shared service credentials.

4. Keep `memory.write_approval: true` during the pilot (spec 17.4).

5. Validate sandboxing (spec 17.5): terminal backend Docker, profile HOME,
   no host secrets in the container environment. Docker is **not**
   installed on the Phase 1a authoring Pi; install Docker plus the pinned
   sandbox image before treating any profile as production (D053).

6. Updates (spec 17.6): users do not self-update stable. A release owner
   announces the SHA and runs `hermes profile update <company>`.

## Promote working → testing → stable (spec 16.7, 21)

- `working`: builders, synthetic/redacted data, sandbox tenants only.
- `testing`: feature branches merge here; staging accounts only.
- `stable`: `main`, production ACL, approved connections only.

```bash
# develop on a feature branch, PR into testing
git checkout -b feat/topic
./tests/run_validation.sh
./scripts/verify-release.sh manifests/company-agent-v0.1.0.yaml .
# after review:
git tag -s v0.1.0 -m "Company agent stable v0.1.0"   # only after spec 35 tests
```

Stable releases need two named humans (D017) and a completed spec 5.8
manifest. `distribution_git_sha` is TODO until the first push.

Rollback is the previous manifest and its pinned artifacts (spec 21.4).

## Validation

```bash
./tests/run_validation.sh
./scripts/verify-release.sh manifests/company-agent-v0.1.0.yaml .
```

Phase 1a recorded output: `tests/VALIDATION-1a.txt`.
