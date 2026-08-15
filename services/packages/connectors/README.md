# Connectors

Credential-free connector layer (spec 12.1, 13.2). Connectors MAY describe
typed tools and field allowlists. They MUST NOT hold tokens, API keys, or
connection strings. Secrets come from the deployment secret system only
(D034) after a human closes the matching decision.

## Live-typed (still NOT_CONFIGURED)

| ID | Module | Tools | Decision |
|---|---|---|---|
| `github_readonly` | `github_readonly.py` | `repo.metadata`, `file.read`, `issues.list` | D042 / D051 / D063 |
| `crm_readonly` | `crm_readonly.py` | `record.read`, `stage.get`, `renewal.read` | D020 / D063 |
| `notion_readonly` | `notion_readonly.py` | `pages.list`, `databases.list`, `page.read`, `comments.list` | D025 / D063 |

Notion is the first company-context importer: notes, docs, and meeting
records in an allowlisted workspace/page scope. The default connector
refuses every action until D025 closes and a secret is bound server-side.

## Later company-context importers

The platform also needs to import company context from other systems.
These IDs are reserved in `FUTURE_CONNECTORS`. They are documented only.

| ID | Typical objects | Notes |
|---|---|---|
| `google_drive` | files, folders | Allowlisted shared drives only |
| `google_docs` | documents | Export to plain text / markdown before ingest |
| `slack` | channels, threads | Channel allowlist; treat messages as untrusted evidence |
| `confluence` | spaces, pages | Space allowlist |
| `onedrive` | files | Tenant + folder allowlist |
| `email` | mailbox metadata / bodies | Personal vs shared mailbox is a D024 decision |

## How a future connector plugs in

1. Add `packages/connectors/<id>.py` with:
   - a field allowlist per tool
   - `ConnectorAction` tuples
   - a `Connector` subclass whose default `configured = False`
   - `invoke()` that calls `RequestContext.require(ctx)` and returns
     `not_configured` until the secret system binds credentials
2. Register the module in `CONNECTOR_REGISTRY` and, if it is not yet
   implemented, keep the id in `FUTURE_CONNECTORS`.
3. Extend `ingest_from_connector()` only by accepting the new
   `connector_id` and mapping document fields → `text` / `title`.
   Reuse `run_ingestion` / `bulk_import_dry_run` for normalize/chunk.
4. Add tests in `tests/test_connectors.py`: refuse without
   `RequestContext`, refuse when unconfigured, allowlist drops extra
   fields, `contains_credential_value(...)` is false on the connector
   object.
5. Close the matching D-item before any live network call.

Ingestion path: connector docs → raw evidence store → normalize/chunk
(with provenance + quarantine). Dry-run is the default. Live persist
and live Notion connect remain TODO (D025, D032, D055).
