-- 0007_claims_research_jobs.sql
-- Spec 14.1 / 14.3 / 24 / 26. Claims and packets cite source locators, not raw blobs.

CREATE TABLE entities (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  canonical_name text NOT NULL,
  entity_type text NOT NULL,
  aliases text[] NOT NULL DEFAULT '{}',
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE claims (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  claim_id text UNIQUE NOT NULL,
  scope_id uuid NOT NULL REFERENCES scopes(id),
  subject_entity_id uuid REFERENCES entities(id),
  statement text NOT NULL,
  predicate text,
  object_text text,
  kind text NOT NULL DEFAULT 'fact',
  valid_from timestamptz,
  valid_until timestamptz,
  confidence numeric(4,3),
  status claim_status NOT NULL DEFAULT 'candidate',
  created_by uuid REFERENCES principals(id),
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Evidence is a locator back to a chunk / source, never a raw dump.
CREATE TABLE claim_evidence (
  claim_id uuid NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
  chunk_id uuid NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
  source_id uuid NOT NULL REFERENCES sources(id),
  locator text NOT NULL,
  stance text NOT NULL CHECK (stance IN ('supports', 'contradicts', 'mentions')),
  excerpt text,
  PRIMARY KEY (claim_id, chunk_id, stance)
);

CREATE TABLE research_packets (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  packet_id text UNIQUE NOT NULL,
  scope_id uuid NOT NULL REFERENCES scopes(id),
  created_by uuid NOT NULL REFERENCES principals(id),
  question text NOT NULL,
  freshness_requirement text NOT NULL DEFAULT 'unspecified',
  decision_risk text NOT NULL DEFAULT 'low',
  status text NOT NULL DEFAULT 'draft',
  query_log jsonb NOT NULL DEFAULT '[]'::jsonb,
  conclusion text,
  created_at timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz
);

CREATE TABLE research_packet_citations (
  packet_id uuid NOT NULL REFERENCES research_packets(id) ON DELETE CASCADE,
  claim_id uuid NOT NULL REFERENCES claims(id),
  source_id uuid NOT NULL REFERENCES sources(id),
  locator text NOT NULL,
  PRIMARY KEY (packet_id, claim_id, source_id, locator)
);

CREATE TABLE ingestion_jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id uuid REFERENCES sources(id),
  document_version_id uuid REFERENCES document_versions(id),
  job_type text NOT NULL,
  state text NOT NULL DEFAULT 'queued',
  dry_run boolean NOT NULL DEFAULT false,
  attempts integer NOT NULL DEFAULT 0,
  run_after timestamptz NOT NULL DEFAULT now(),
  locked_by text,
  locked_at timestamptz,
  last_error text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX ingestion_jobs_ready_idx ON ingestion_jobs(state, run_after)
  WHERE state IN ('queued', 'retry');
