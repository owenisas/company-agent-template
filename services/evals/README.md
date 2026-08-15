# Knowledge eval harness (placeholder)

Phase 2 scaffold. No eval implementation. Do not run live retrieval.

## What later evals MUST measure

1. Retrieval quality
   - lexical + vector + RRF recall/precision on a pinned fixture corpus
   - stale vs current source preference
   - no silent promotion of candidate claims

2. Zero unauthorized retrieval
   - employee A never receives employee B private/restricted rows
   - `automation` never receives user-private rows or employee OAuth scopes
   - unknown capability / unknown connection deny
   - deleted and restricted sources disappear from search (propagation)

3. Citation exactness
   - every cited claim renders `{source_id}@{locator}`
   - locator includes chunk/page/char/clause as applicable
   - circular citation / summary-of-summary inflation is flagged

## Non-goals for this folder right now

- No golden-set runner
- No model calls
- No network
- No database

Blocked by D040 (embeddings), D055 (postgres host), D020–D024 (data scope).
