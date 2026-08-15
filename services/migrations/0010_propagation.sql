-- 0010_propagation.sql
-- Phase 2 exit criterion: a deleted/restricted source propagates correctly.
-- Spec 31.5 / data-classification-retention.md §5.
--
-- Design (function stub — not scheduled, not enabled):
--
--   source status        -> deleted / tombstoned
--   raw object           -> deleted, or retained only under legal hold
--   chunks               -> removed / inaccessible
--   embeddings           -> removed
--   summaries / claims   -> removed, rejected, or re-linked
--   search caches        -> invalidated
--   research outputs     -> mark source unavailable; preserve audit lineage
--   backups              -> expire according to backup retention
--
-- Legal hold overrides ordinary deletion.

CREATE OR REPLACE FUNCTION propagate_source_restriction(
  p_source_uuid uuid,
  p_new_status source_status,
  p_actor text
) RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
  -- Scaffold stub. MUST NOT be called from an agent shell.
  -- TODO: D016 who MAY change classification; D036 retention exceptions.
  IF p_new_status NOT IN ('deleted', 'legal_hold', 'quarantined') THEN
    RAISE EXCEPTION 'unsupported propagation status %', p_new_status;
  END IF;

  UPDATE sources
     SET status = p_new_status,
         deleted_at = CASE WHEN p_new_status = 'deleted' THEN now() ELSE deleted_at END
   WHERE id = p_source_uuid
     AND legal_hold = false;

  -- Hide derived retrieval units. Do not rewrite audit lineage.
  IF p_new_status = 'deleted' THEN
    DELETE FROM chunk_embeddings
     WHERE chunk_id IN (SELECT id FROM chunks WHERE source_id = p_source_uuid);

    DELETE FROM chunks
     WHERE source_id = p_source_uuid;

    UPDATE documents
       SET state = 'deleted', deleted_at = now()
     WHERE source_id = p_source_uuid;

    UPDATE claims
       SET status = 'rejected'
     WHERE id IN (
       SELECT claim_id FROM claim_evidence WHERE source_id = p_source_uuid
     );
  END IF;

  INSERT INTO audit_events (
    trace_id, event_type, executing_principal, release_id, result, details_redacted
  ) VALUES (
    'propagate',
    'source.restrict',
    p_actor,
    'scaffold',
    'stub',
    jsonb_build_object('source_id', p_source_uuid, 'status', p_new_status)
  );
END;
$$;

COMMENT ON FUNCTION propagate_source_restriction(uuid, source_status, text) IS
  'Phase 2 scaffold stub for deleted/restricted propagation (spec 31.5). Not enabled.';
