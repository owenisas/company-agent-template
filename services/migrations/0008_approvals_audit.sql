-- 0008_approvals_audit.sql
-- Spec 14.3 approvals + audit_events. Audit is append-only.

CREATE TABLE approvals (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  approval_id text UNIQUE NOT NULL,
  trace_id text NOT NULL,
  requested_by uuid NOT NULL REFERENCES principals(id),
  action_type text NOT NULL,
  action_fingerprint text NOT NULL,
  risk_tier text NOT NULL,
  parameters_redacted jsonb NOT NULL,
  state text NOT NULL,
  expires_at timestamptz NOT NULL,
  approved_by uuid[] NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now(),
  decided_at timestamptz
);

CREATE TABLE audit_events (
  id bigserial PRIMARY KEY,
  occurred_at timestamptz NOT NULL DEFAULT now(),
  trace_id text NOT NULL,
  request_id text,
  event_type text NOT NULL,
  requesting_principal_id uuid REFERENCES principals(id),
  executing_principal text,
  profile_id text,
  release_id text NOT NULL,
  scope text,
  approval_id text,
  skill_id text,
  plugin_id text,
  tool_id text,
  connection_id text,
  business_object_type text,
  business_object_id text,
  result text,
  input_hash text,
  output_hash text,
  details_redacted jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX audit_events_trace_idx ON audit_events(trace_id);
CREATE INDEX audit_events_time_idx ON audit_events(occurred_at);

-- No UPDATE/DELETE grants for the app role on audit_events (applied in 0009).
