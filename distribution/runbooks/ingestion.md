# Runbook: ingestion

Spec 22.1 (notes are evidence), skill `note-ingestion`.

1. Identify source, owner, capture date, and classification.
2. If any of those are unknown, do not ingest production data (spec 34).
3. Store the original. Extract unverified claims only.
4. Never copy secrets into the packet, USER.md, or memory.
5. Restricted legal/HR/customer items need the domain owner first.
6. Return status and errors. Do not silently retry destructive transforms.
