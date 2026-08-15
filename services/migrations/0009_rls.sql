-- 0009_rls.sql
-- Spec 14.4 Access control enforcement. Phase 2 deliverable: ACL/RLS.
--
-- =============================================================================
-- Visibility model (app + DB MUST stay in sync)
-- =============================================================================
-- Authoritative logic lives in packages/knowledge/retrieval.py
-- (build_acl_clause, app_prefilter_allows, sql_rls_claims_gate). This file is
-- the database mirror. If one changes, the other MUST change in the same PR.
--
-- Four readable paths, after deleted/quarantined-untrusted rows are excluded:
--   1. owner-private     — owner_principal.external_id = request principal
--   2. team-project      — visibility IN ('team','project') AND scopes.slug
--                          is in the requester's memberships
--   3. company-public    — visibility IN ('company','public')
--   4. restricted-with-source_acl
--                        — explicit source_acl grant (principal or scope)
--
-- Restricted classification: not readable unless the requester is the owner,
-- holds a restricted-domain membership, or has a source_acl grant.
-- Service principals never see private or restricted rows (spec 15.3, 29.1).
-- System (company-system) sees non-deleted rows for control-plane work only.
--
-- Claims are NOT independently visible. claims_select_via_evidence requires
-- claim_evidence → chunks → sources, and at least one of those sources must
-- be readable under the model above. A claim with no matching evidence is deny.
--
-- Session GUCs the app MUST SET LOCAL before any query (spec 24.3). The app
-- prefilter uses bind params :acl_principal_slug / :acl_memberships; the same
-- values MUST also be installed as:
--   SET LOCAL request.principal_slug  = '<validated slug>';
--   SET LOCAL request.principal_type  = 'employee' | 'service' | 'system';
--   SET LOCAL request.purpose         = '<purpose>';
--   SET LOCAL acl.memberships         = '{slug1,slug2}';  -- text[] literal
-- Do not retrieve then filter. Do not let a prompt set these.
--
-- TODO: empty/malformed acl.memberships is treated as {} (fail closed).
-- A live join against memberships(principal_id, scope_id) instead of the GUC
-- is expressible in SQL but is not wired until D055 (postgres host / kb_app).
-- =============================================================================

ALTER TABLE sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE claims ENABLE ROW LEVEL SECURITY;
ALTER TABLE research_packets ENABLE ROW LEVEL SECURITY;
ALTER TABLE raw_objects ENABLE ROW LEVEL SECURITY;

ALTER TABLE sources FORCE ROW LEVEL SECURITY;
ALTER TABLE notes FORCE ROW LEVEL SECURITY;
ALTER TABLE documents FORCE ROW LEVEL SECURITY;
ALTER TABLE chunks FORCE ROW LEVEL SECURITY;
ALTER TABLE claims FORCE ROW LEVEL SECURITY;
ALTER TABLE research_packets FORCE ROW LEVEL SECURITY;
ALTER TABLE raw_objects FORCE ROW LEVEL SECURITY;

-- Helper: current request principal slug (set by the API, never by a prompt).
-- SELECT set_config('request.principal_slug', 'employee-a', true);
-- SELECT set_config('request.principal_type', 'employee', true);
-- SELECT set_config('acl.memberships', '{all-employees,engineering}', true);

CREATE OR REPLACE FUNCTION acl_memberships_guc()
RETURNS text[]
LANGUAGE sql
STABLE
AS $$
  SELECT COALESCE(NULLIF(current_setting('acl.memberships', true), ''), '{}')::text[];
$$;

CREATE OR REPLACE FUNCTION source_row_readable(
  p_slug text,
  p_type text,
  p_memberships text[],
  p_deleted_at timestamptz,
  p_status source_status,
  p_instruction_trust text,
  p_visibility visibility_scope,
  p_classification data_classification,
  p_owner_id uuid,
  p_scope_id uuid,
  p_source_id uuid
) RETURNS boolean
LANGUAGE sql
STABLE
SECURITY INVOKER
AS $$
  SELECT
    p_deleted_at IS NULL
    AND p_status <> 'deleted'
    AND NOT (p_status = 'quarantined' AND p_instruction_trust <> 'none')
    AND (
      p_type = 'system'
      OR (
        (
          EXISTS (
            SELECT 1 FROM principals p
            WHERE p.id = p_owner_id AND p.external_id = p_slug
          )
          OR p_visibility IN ('company', 'public')
          OR (
            p_visibility IN ('team', 'project')
            AND EXISTS (
              SELECT 1 FROM scopes sc
              WHERE sc.id = p_scope_id
                AND sc.slug = ANY(p_memberships)
            )
          )
          OR EXISTS (
            SELECT 1 FROM source_acl a
            JOIN principals p ON p.id = a.subject_id
            WHERE a.source_id = p_source_id
              AND a.subject_type = 'principal'
              AND a.permission IN ('read', 'annotate', 'curate', 'admin')
              AND p.external_id = p_slug
          )
          OR EXISTS (
            SELECT 1 FROM source_acl a
            JOIN scopes sc ON sc.id = a.subject_id
            WHERE a.source_id = p_source_id
              AND a.subject_type = 'scope'
              AND a.permission IN ('read', 'annotate', 'curate', 'admin')
              AND sc.slug = ANY(p_memberships)
          )
        )
        AND NOT (
          p_visibility = 'private'
          AND NOT EXISTS (
            SELECT 1 FROM principals p
            WHERE p.id = p_owner_id AND p.external_id = p_slug
          )
          AND p_type <> 'system'
        )
        AND NOT (
          p_type = 'service'
          AND (p_visibility = 'private' OR p_classification = 'restricted')
        )
        AND (
          p_classification <> 'restricted'
          OR EXISTS (
            SELECT 1 FROM principals p
            WHERE p.id = p_owner_id AND p.external_id = p_slug
          )
          OR p_memberships && ARRAY[
            'legal-approvers',
            'finance-approvers',
            'people-hr-approvers',
            'customer-data-approvers',
            'agent-platform-admins'
          ]::text[]
          OR EXISTS (
            SELECT 1 FROM source_acl a
            JOIN principals p ON p.id = a.subject_id
            WHERE a.source_id = p_source_id
              AND a.subject_type = 'principal'
              AND a.permission IN ('read', 'annotate', 'curate', 'admin')
              AND p.external_id = p_slug
          )
          OR EXISTS (
            SELECT 1 FROM source_acl a
            JOIN scopes sc ON sc.id = a.subject_id
            WHERE a.source_id = p_source_id
              AND a.subject_type = 'scope'
              AND a.permission IN ('read', 'annotate', 'curate', 'admin')
              AND sc.slug = ANY(p_memberships)
          )
        )
      )
    );
$$;

-- can_read_claim(principal_slug, memberships, claim_id)
-- Infer type from the known slug enum (packages/authz/principals.py).
-- Unknown slug => deny. Reads request.principal_type only as a cross-check
-- when set; a mismatch is deny (fail closed).
CREATE OR REPLACE FUNCTION can_read_claim(
  principal_slug text,
  memberships text[],
  p_claim_id uuid
) RETURNS boolean
LANGUAGE sql
STABLE
SECURITY INVOKER
AS $$
  WITH inferred AS (
    SELECT CASE
      WHEN principal_slug = 'company-system' THEN 'system'
      WHEN principal_slug = 'automation' THEN 'service'
      WHEN principal_slug IN ('employee-a', 'employee-b', 'employee-c') THEN 'employee'
      ELSE NULL
    END AS p_type
  )
  SELECT EXISTS (
    SELECT 1
    FROM claim_evidence ce
    JOIN chunks ch ON ch.id = ce.chunk_id
    JOIN sources s ON s.id = ch.source_id AND s.id = ce.source_id
    CROSS JOIN inferred i
    WHERE ce.claim_id = p_claim_id
      AND i.p_type IS NOT NULL
      AND (
        current_setting('request.principal_type', true) IS NULL
        OR current_setting('request.principal_type', true) = ''
        OR current_setting('request.principal_type', true) = i.p_type
      )
      AND source_row_readable(
        principal_slug,
        i.p_type,
        COALESCE(memberships, '{}'::text[]),
        s.deleted_at,
        s.status,
        s.instruction_trust,
        s.visibility,
        s.classification,
        s.owner_principal_id,
        s.scope_id,
        s.id
      )
  );
$$;

CREATE POLICY sources_select_acl ON sources
  FOR SELECT
  USING (
    source_row_readable(
      current_setting('request.principal_slug', true),
      current_setting('request.principal_type', true),
      acl_memberships_guc(),
      sources.deleted_at,
      sources.status,
      sources.instruction_trust,
      sources.visibility,
      sources.classification,
      sources.owner_principal_id,
      sources.scope_id,
      sources.id
    )
  );

CREATE POLICY notes_select_via_source ON notes
  FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM sources s
      WHERE s.id = notes.source_id
      -- RLS on sources is checked independently when selected;
      -- this clause keeps notes from leaking a deleted/restricted parent.
      AND s.deleted_at IS NULL
      AND s.status <> 'deleted'
    )
  );

CREATE POLICY chunks_select_via_source ON chunks
  FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM sources s
      WHERE s.id = chunks.source_id
        AND s.deleted_at IS NULL
        AND s.status <> 'deleted'
    )
  );

CREATE POLICY documents_select_via_source ON documents
  FOR SELECT
  USING (
    deleted_at IS NULL
    AND EXISTS (
      SELECT 1 FROM sources s
      WHERE s.id = documents.source_id
        AND s.deleted_at IS NULL
        AND s.status <> 'deleted'
    )
  );

DROP POLICY IF EXISTS claims_select_scoped ON claims;

CREATE POLICY claims_select_via_evidence ON claims
  FOR SELECT
  USING (
    can_read_claim(
      current_setting('request.principal_slug', true),
      acl_memberships_guc(),
      claims.id
    )
  );

CREATE POLICY research_packets_select ON research_packets
  FOR SELECT
  USING (
    created_by IN (
      SELECT id FROM principals
      WHERE external_id = current_setting('request.principal_slug', true)
    )
    OR current_setting('request.principal_type', true) = 'system'
  );

-- Service role for the API: SELECT/INSERT on working tables; INSERT-only on audit.
-- TODO: D055 create roles kb_app / kb_audit once postgres exists. Do not grant
-- table owner rights to the agent shell (spec 5.2, 12.2).
