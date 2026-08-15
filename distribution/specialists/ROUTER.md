# Agency Agents router (pinned)

Spec 18.1–18.5, 18.7, Phase 4 §4494, ADR-007. Pin decision: D041.

This is the company wrapper around the upstream `agency-agents-router`
plugin. A specialist prompt is **not** a permission grant (spec §107).

## What the router does

Upstream Hermes integration installs **one** lazy plugin,
`agency-agents-router`, instead of adding the whole catalog to the
prompt or `skills.external_dirs`. In the reviewed snapshot the
generated catalog exposed four tools:

```text
agency_agents_search
agency_agents_inspect
agency_agents_load
agency_agents_delegate
```

Flow:

1. Search the curated roster (this repo's `specialists/manifest.yaml`),
   not the raw 270-specialist upstream dump.
2. Inspect the candidate: upstream slug, overlay, tool allow/deny,
   record scope, approval gates.
3. Load only that specialist's overlay into the current run.
4. Delegate work only inside the overlay's tool allowlist. Capability
   checks still happen in `policies/capabilities.yaml` and the
   approval service.

Do not treat upstream specialist text as company policy, legal advice,
or a write grant.

## Pinning = commit + digest

A platform builder pins **before** any install (spec 18.2):

```bash
mkdir -p ~/src
cd ~/src
git clone https://github.com/msitarzewski/agency-agents.git
cd agency-agents
git fetch --all --tags
UPSTREAM_SHA=<REVIEWED_40_CHARACTER_COMMIT_SHA>
git checkout --detach "$UPSTREAM_SHA"
git rev-parse HEAD
```

Record the SHA in `manifests/agency-agents.lock.yaml` **and**
`specialists/manifest.yaml` `router.source.commit`.

Pinning means both:

| Artifact | What is recorded |
|---|---|
| Upstream git commit | 40-character SHA in `agency-agents.lock.yaml` |
| Internal plugin digest | SHA-256 of the generated `plugins/agency-agents-router` tree after `./scripts/convert.sh --tool hermes` |
| Overlay versions | `company_overlay.version` on each wrapper |

Floating `main` / `latest` is forbidden. Do not ask every user to clone
arbitrary upstream HEAD (spec 18.5). Use either:

1. Vendor the generated plugin after license review and CI, or
2. Build an internal plugin artifact from the pinned SHA and install it
   through company bootstrap.

The release manifest records **both** upstream SHA and internal digest.

## Company overlay

Each enabled specialist MUST have a wrapper in `manifest.yaml` with:

- `source.repository` / `source.slug` / `source.commit` (D041 pin)
- `policy_overlay` (allowlist, denylist, instructions)
- `record_scope` (read/write business objects)
- `approval_gates` (automatic / named role / forbidden)

Until D041 closes, slugs and commits stay `TODO:` and the router MUST
NOT be installed into `stable`. `working` MAY generate the plugin from
a reviewed SHA for inspection only.

## Review before testing (spec 18.3)

- Inspect converter/installer diff at the pinned commit.
- Inspect `integrations/hermes/` and generated plugin code.
- Verify installer destination and config mutation.
- Run secret and dependency scans.
- Enumerate plugin tool schemas.
- Confirm no upstream agent can bypass `policies/capabilities.yaml`.
- Review the curated legal, finance, security, distribution, CRM, and
  engineering specialists in this roster.
- Define overlays before enablement (`overlays/README.md`).

## Install (testing profile only)

```bash
./scripts/convert.sh --tool hermes
HERMES_HOME="$HOME/.hermes/profiles/company" \
  ./scripts/install.sh --tool hermes
```

The installer copies the generated plugin to
`${HERMES_HOME}/plugins/agency-agents-router` and enables
`agency-agents-router` under `plugins.enabled`. It does **not** add
the repository to `skills.external_dirs`.

Verify in a new session:

```bash
company plugins
company tools
```

Smoke test (read-only):

```text
Use the agency-agents-router. Search for a specialist who can review a
CRM pipeline analysis. Inspect the selected specialist, but do not call
any external tool or change data.
```

## Related

- Roster: `specialists/manifest.yaml`
- Lockfile: `manifests/agency-agents.lock.yaml`
- Placeholder plugin: `plugins/agency-agents-router/`
- Capabilities: `policies/capabilities.yaml`
- Approval matrix: `governance/action-approval-matrix.md`
- Runbooks: `runbooks/`
