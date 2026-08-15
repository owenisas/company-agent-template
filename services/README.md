# company-agent-services

<Company> company Hermes agent services. This repository is the Phase 2–3
**scaffold**: code structure, schema, and unit-testable logic. It is not a
running control plane.

Normative spec: `company-agent-platform` v1.1 §§12, 13.2–13.4, 14, 15.4, 30.2,
30.3, 36.1, Phase 2–3. Governance: `docs/governance/*`. Decisions: D001–D063.

## Phase boundary

| This scaffold does | This scaffold does not |
|---|---|
| Authz + capability registry | Issue credentials |
| Approval create/validate/resolve (in-memory) | Notify approvers or broker secrets |
| ACL SQL prefilter | Connect PostgreSQL |
| Read-only GitHub/CRM MCP tool shapes | Call GitHub or a CRM |
| Connection references (opaque handles) | Store or resolve real secrets |
| Preview/apply + attribution predicates | Start services, cron, or Docker |

Stubs return `not_configured` or `TODO:` plus a D-item. They never pretend to work.

## What blocks each runtime piece

| Runtime piece | Blocked by |
|---|---|
| Concrete CRM / contracts / finance / publish connectors | D020–D024 data scope |
| GitHub org remotes / CODEOWNERS | D042 `<GITHUB_ORG>` |
| Named approvers / approval UX | D011–D018, D049 |
| Approval fingerprint / TTL / reference format | D060–D062 (scaffold defaults only) |
| Docker Compose / pgvector image | D053; Docker is not installed |
| Embeddings and vector(N) | D040 / D056 |
| PostgreSQL on the control-plane host | D055 |
| Identity / JWT to this API | D035 |

## How tests run

Offline only. No database, no network.

```text
python3 -m pytest tests/ -x -q
```

Scratch venv (not system-wide):

```text
uv venv /tmp/p3venv
VIRTUAL_ENV=/tmp/p3venv uv pip install pytest pydantic fastapi httpx
/tmp/p3venv/bin/python -m pytest tests/ -x -q
```

See `tests/README.md` and `evals/README.md`.

## Layout

Matches spec 13.3 plus Phase 3 packages:

`apps/` (knowledge_*, approval_api, audit_consumer, github_readonly_mcp, crm_readonly_mcp)

`packages/` {authz, knowledge, tracing, connectors, capabilities, approval, connections, actions}
