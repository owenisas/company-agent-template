# ADR-0001: Initial platform decisions (template)

**Status:** Proposed — fill and accept before treating the fork as a production control plane
**Date:** TODO: `<YYYY-MM-DD>`
**Company slug:** `<company>`
**Deciders:** TODO: named humans
**Normative sources:** spec Sections 2, 5.2, 5.5, 5.7, 5.8, 8, 9, 11.3, 12, 15.3–15.6, 28, 29, 31, 34 Phase 0, 37, 38, 39, Appendix D
**Supersedes:** none

## Context

`<Company>` is adopting the Company Hermes Agent Platform specification v1.1. Spec Section 8 requires this ADR before build. Spec Section 5.5 allows a small company to begin with one host for the control plane and a logically isolated worker path.

Company-specific systems (CRM, contracts, finance, publishing, GitHub org, model provider, region) MUST remain `TODO:` in `DECISIONS-NEEDED-template.md` (forked as `DECISIONS-NEEDED.md`) until a human decides. Accepting this ADR accepts architecture defaults; it does not authorize production data connections.

## Decision

Adopt the spec Section 8 recommended initial answers unless a later ADR records a change.

### Section 8 decision record

| # | Decision | Adopted initial answer | Notes |
|---|---|---|---|
| 1 | Interactive profile location | On each company workstation; central services remote | TODO: confirm |
| 2 | Shared control-plane location | Private Ubuntu 24.04 LTS VPS/cloud VM on a private/identity-controlled path (spec 5.2) | One-host startup is allowed (spec 5.5) |
| 3 | Automation profile location | Control-plane host; service identity `automation`; tool-only by default | Spec 15.3–15.6. MUST NOT copy an employee profile. |
| 4 | Task code execution | Employee Docker sandbox for short work; restricted remote worker for unattended/heavy jobs | On one host, the worker MUST be logically isolated |
| 5 | Automation shell policy | No generic shell on the control-plane host; arbitrary code routes to a worker | Spec 5.2 |
| 6 | Model provider | One approved primary, one fallback; keys separated by environment; hosted inference at launch | TODO: D037 / D038 |
| 7 | Knowledge data region | Same approved region as other company confidential data | TODO: D030 |
| 8 | Raw-object storage | Encrypted server volume, with a versioned S3-compatible target for backups when selected | TODO: D032 |
| 9 | Secrets provider | Existing managed provider if the company already has one | TODO: D034 |
| 10 | User authentication to KB/MCP | Short-lived user JWT through a private identity proxy; service tokens for automation | TODO: D035 |
| 11 | CRM source of truth | `<CRM_NAME>` | TODO: D020 |
| 12 | Contract source of truth | `<CONTRACT_REPOSITORY>` | TODO: D021 |
| 13 | Finance source of truth | `<FINANCE_SYSTEM>` | TODO: D022 |
| 14 | Publishing channels | `<CHANNEL_LIST>` | TODO: D023. Autonomous external sends disabled at launch. |
| 15 | Stable branch | `main` | Spec 8, 9.3 |
| 16 | Test branch | `testing` | Spec 8, 9.3 |
| 17 | Release approval | Two reviewers for stable policy/plugin changes; one for low-risk skill text | Named humans TODO: D017 |
| 18 | Audit retention | At least 1 year unless legal/compliance requires longer | Spec 8, 31 |
| 19 | Raw note retention | By classification and source; deletion supported | See `data-classification-retention.md` |
| 20 | Personal memory writes | Approval required during pilot | Spec 8 |
| 21 | Skill self-modification | Approval required; company skills changed only by PR | Spec 8 |
| 22 | Autonomous external sends | Disabled at launch | Spec 8 |
| 23 | High-risk credentials | Never exposed to general agent shell; brokered action only | Spec 12.4, 29.5 |
| 24 | Automation split threshold | Split by credential/data boundary, untrusted workload, or sustained capacity pressure | Spec 5.5, 15.7 |

### Additional decisions

| # | Decision | Adopted initial answer |
|---|---|---|
| 25 | Company slug | `<company>` |
| 26 | Employee identifiers | Immutable slugs `employee-a`, `employee-b`, `employee-c` (spec 11.3). Display names TODO. |
| 27 | Service profile name | `automation` |
| 28 | One-host startup | Allowed per spec 5.5 until a split trigger is hit |
| 29 | Control plane | The VPS **is** the shared control plane (spec 5.2). Not just another workstation. |
| 30 | GitHub org / repos | Three private repos as in spec 9.1. Org name TODO: `<GITHUB_ORG>` |
| 31 | Environments | `working` / `testing` / `stable` as spec 5.8 |
| 32 | Classification vocabulary | `public` / `internal` / `confidential` / `restricted` (spec 28.1) |
| 33 | Execution classes | Class A local sandbox, Class B restricted worker, Class C ephemeral isolation, Class D CI (spec 5.4) |
| 34 | Identity substitution | Spec 15.6 is invariant: automation never silently substitutes its identity for a human |

## Consequences

- Phase 0 can complete without inventing CRM, model, or region answers.
- Production connectors stay disconnected until `DECISIONS-NEEDED.md` rows close.
- A later ADR is required if the company substitutes a one-host appliance for the VPS or splits the worker.

## Follow-up

1. Fork `DECISIONS-NEEDED-template.md` → `DECISIONS-NEEDED.md`.
2. Bind employee display names and emails (D001–D004, D019).
3. Name approvers (D011–D018).
4. Select CRM, connectors, model provider, region, backups (D020–D025, D030, D033, D037).
