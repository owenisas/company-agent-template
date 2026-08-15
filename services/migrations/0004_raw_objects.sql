-- 0004_raw_objects.sql
-- Spec 14.1 raw evidence store, 14.5 content-addressed objects, 22.6 raw layer.
-- Exit criterion: raw and derived data are separable.
-- Raw payloads MUST NOT be copied into chunks / claims / research_packets.

CREATE TABLE raw_objects (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  content_sha256 text NOT NULL,
  object_key text NOT NULL UNIQUE,
  mime_type text,
  byte_length bigint NOT NULL DEFAULT 0,
  -- Payload lives in object storage (TODO: D032 backend). Relational table holds
  -- only the handle. Do not add a bytea/text payload column to derived tables.
  payload_ref text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX raw_objects_sha_idx ON raw_objects(content_sha256);
