# Capacity plan

Phase 5 §4515. Spec §6.1 / §6.2 (table at spec line 473).

Planning for **three named employees** + `company-automation` +
knowledge stack + occasional browser tasks. Not a vendor SLA.

## Sizing

| Resource | Minimum practical | Recommended start | Why |
|---|---|---|---|
| CPU | 4 vCPU | 8 vCPU | Ingestion, three users, automation, and browser tasks can overlap |
| RAM | 16 GB | 32 GB | Browser automation and local reranking are bursty |
| Disk | 250 GB encrypted SSD | 500 GB+ encrypted SSD | Notes, attachments, DB, worktrees, logs, local backups |
| Backup capacity | 2x active data | 3x active data | DB + objects + git mirrors + manifests + config |
| Network | Private IPv4/IPv6 or VPN | Private + outbound allow policy | No public DB/MCP |

VPS floor for this scaffold: **do not go below 8 GB RAM**. 8 GB can
host the control plane in a pinch (serve + desktop-web + empty
Postgres) but **will not** comfortably run three concurrent users
plus knowledge embeddings plus a browser worker. Spec minimum for
that mix is **16 GB**; prefer **32 GB**.

No GPU on this VPS. Use a hosted embedding/model endpoint (D040).

## What lives on the box

- Hermes profiles (3 humans + automation)
- `hermes-serve` + `hermes-desktop-web` (loopback, SSO in front)
- Compose: postgres+pgvector, knowledge-api/worker/mcp, approval-api,
  audit-consumer
- Optional: browser worker / restricted exec (D031)
- Local dump directory (rotated; off-host is D033)

## Scale-out triggers (spec 6.2)

Move Postgres, object storage, or the worker **off** this VPS before
adding more CPU when the constraint is blast radius, data
sensitivity, or noisy tasks — not raw capacity.

Split `company-automation` when credential/data boundaries or
sustained capacity pressure appear (spec 15).

## Observability budget

A lightweight collector (compose profile `observability`, provider
TODO) should stay under ~512 MB RSS. Alert list: spec 30.5.
