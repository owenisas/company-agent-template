# Evals (scaffold)

Phase 2 knowledge evals plus Phase 4 business-domain evals.
**No implementation in this folder.** Do not run live retrieval, model
calls, network, or a database.

## What later evals MUST measure

### A. Knowledge (Phase 2 — unchanged)

1. Retrieval quality — lexical + vector + RRF on a pinned fixture
   corpus; stale vs current preference; no silent promotion.
2. Zero unauthorized retrieval — employee A never receives employee B
   private rows; automation never receives user-private rows; unknown
   capability/connection deny; deleted sources disappear.
3. Citation exactness — `{source_id}@{locator}` on every cited claim.

### B. Business-domain (Phase 4)

Each `SPECS-*.md` file is a stub spec. A future runner MUST score:

1. **Specialist correctness**
   - Router picks a specialist from the matching domain pack.
   - Task-scoped context only (no legal matter in a campaign draft).
   - Overlay tool allowlist is the only tool set offered.

2. **Prohibited-action refusal**
   - Sign, pay, unrestricted delete, privilege grant, autonomous
     send/publish are refused even when the user says "yes, just do
     it" or a retrieved page instructs it.
   - Refusal is enforced by capability policy, not prompt text.

3. **Approval-gate compliance**
   - Writes produce a preview + hash before apply.
   - Apply without a matching unconsumed approval fails.
   - Drifted payload with the same token fails.
   - Forbidden actions stay forbidden after a chat approval.

## Spec files

| File | Domain runbook |
|---|---|
| `SPECS-lead-to-cash.md` | `runbooks/lead-to-cash.md` |
| `SPECS-contract.md` | `runbooks/contract.md` |
| `SPECS-campaign.md` | `runbooks/campaign.md` |
| `SPECS-renewal.md` | `runbooks/renewal.md` |
| `SPECS-procure-to-pay.md` | `runbooks/procure-to-pay.md` |
| `SPECS-code-release.md` | `runbooks/code-release.md` |

Research remains covered by the knowledge suite plus
`runbooks/research.md` (no separate SPECS file).

## Non-goals right now

- No golden-set runner
- No model calls
- No network
- No database

Blocked by D040 (embeddings), D055 (postgres host), D020–D024 (data
scope), D041 (roster pin), D011–D018 (named approvers).
