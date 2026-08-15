-- 0001_extensions.sql
-- Spec 14.1 PostgreSQL / pgvector. MUST NOT be applied on this host in Phase 2 scaffold.
-- TODO: D055 postgres host on the control plane; D053 docker image pin; D040/D056 embedding dimensions.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
