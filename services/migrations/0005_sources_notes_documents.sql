-- 0005_sources_notes_documents.sql
-- Spec 14.3 documents + 22.2 source object + 24.2 source/note.
-- `sources` is the evidence record. `notes` is the user-facing typed row.
-- `documents` / `document_versions` hold normalized derived text, not raw bytes.
-- Retention flags: legal_hold, retention_hold, retention_class, retain_until.

CREATE TABLE sources (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id text UNIQUE NOT NULL,
  workspace_id text NOT NULL DEFAULT 'company',
  owner_principal_id uuid NOT NULL REFERENCES principals(id),
  scope_id uuid NOT NULL REFERENCES scopes(id),
  visibility visibility_scope NOT NULL DEFAULT 'private',
  source_type text NOT NULL,
  title text,
  origin_uri text,
  external_id text,
  author_name text,
  published_at timestamptz,
  captured_at timestamptz NOT NULL DEFAULT now(),
  content_sha256 text NOT NULL,
  raw_object_id uuid NOT NULL REFERENCES raw_objects(id),
  classification data_classification NOT NULL DEFAULT 'internal',
  retention_class text NOT NULL DEFAULT 'research-evidence',
  retain_until timestamptz,
  legal_hold boolean NOT NULL DEFAULT false,
  retention_hold boolean NOT NULL DEFAULT false,
  trust_prior text NOT NULL DEFAULT 'unverified',
  instruction_trust text NOT NULL DEFAULT 'none',
  status source_status NOT NULL DEFAULT 'quarantined',
  deleted_at timestamptz,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX sources_scope_hash_active
  ON sources(scope_id, content_sha256)
  WHERE deleted_at IS NULL;

CREATE TABLE source_acl (
  source_id uuid NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
  subject_type text NOT NULL CHECK (subject_type IN ('principal', 'scope')),
  subject_id uuid NOT NULL,
  permission text NOT NULL CHECK (permission IN ('read', 'annotate', 'curate', 'admin')),
  PRIMARY KEY (source_id, subject_type, subject_id, permission)
);

-- User-facing notes: derived metadata only. Body is in sources/raw_objects.
CREATE TABLE notes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  note_id text UNIQUE NOT NULL,
  source_id uuid NOT NULL REFERENCES sources(id),
  owner_principal_id uuid NOT NULL REFERENCES principals(id),
  title text,
  visibility visibility_scope NOT NULL DEFAULT 'private',
  classification data_classification NOT NULL DEFAULT 'internal',
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Normalized / versioned derived text (spec 14.3 document_versions).
CREATE TABLE documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id uuid NOT NULL REFERENCES sources(id),
  owner_principal_id uuid REFERENCES principals(id),
  scope_id uuid NOT NULL REFERENCES scopes(id),
  source_type text NOT NULL,
  source_locator text,
  classification data_classification NOT NULL DEFAULT 'internal',
  state document_state NOT NULL DEFAULT 'inbox',
  retention_class text NOT NULL,
  content_sha256 text NOT NULL,
  deleted_at timestamptz,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE document_versions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  version_no integer NOT NULL,
  raw_object_id uuid NOT NULL REFERENCES raw_objects(id),
  object_key text NOT NULL,
  mime_type text,
  byte_length bigint,
  extraction_status text NOT NULL DEFAULT 'pending',
  extracted_text text,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(document_id, version_no)
);
