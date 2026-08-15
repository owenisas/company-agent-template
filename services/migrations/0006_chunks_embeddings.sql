-- 0006_chunks_embeddings.sql
-- Spec 14.1 / 14.3 chunks + tsvector FTS + embedding vector + indexes.
-- Derived layer only: provenance via source_id / raw_object_id / offsets.
-- TODO: D040 / D056 — vector dimension is a placeholder (1536). Changing
-- dimensions later MUST create a parallel embedding table, backfill, switch
-- reads, then retire the old model (spec 14.3).

CREATE TABLE chunks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id uuid NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
  document_version_id uuid REFERENCES document_versions(id) ON DELETE CASCADE,
  raw_object_id uuid NOT NULL REFERENCES raw_objects(id),
  ordinal integer NOT NULL,
  content text NOT NULL,
  token_count integer,
  char_start integer,
  char_end integer,
  page_start integer,
  page_end integer,
  heading_path text[],
  search_vector tsvector GENERATED ALWAYS AS
    (to_tsvector('english', coalesce(content, ''))) STORED,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  UNIQUE(source_id, ordinal)
);

CREATE INDEX chunks_fts_idx ON chunks USING gin(search_vector);
CREATE INDEX chunks_source_idx ON chunks(source_id);

CREATE TABLE chunk_embeddings (
  chunk_id uuid PRIMARY KEY REFERENCES chunks(id) ON DELETE CASCADE,
  embedding_model text NOT NULL,
  embedding_version text NOT NULL,
  -- Placeholder dimension until D040 closes. Do not apply blindly.
  embedding vector(1536) NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX chunk_embeddings_hnsw_idx
  ON chunk_embeddings USING hnsw (embedding vector_cosine_ops);
