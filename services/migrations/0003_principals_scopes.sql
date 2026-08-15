-- 0003_principals_scopes.sql
-- Spec 14.1 / 14.3 principals, scopes, memberships, ACLs.
-- Slugs MUST match governance user-role-group-registry.md.

CREATE TABLE principals (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  external_id text UNIQUE NOT NULL,
  principal_type principal_type NOT NULL,
  display_name text NOT NULL,
  active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT principals_slug_known CHECK (
    external_id IN (
      'employee-a',
      'employee-b',
      'employee-c',
      'automation',
      'company-system'
    )
  )
);

CREATE TABLE scopes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  scope_type text NOT NULL,
  slug text UNIQUE NOT NULL,
  parent_id uuid REFERENCES scopes(id),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE memberships (
  principal_id uuid NOT NULL REFERENCES principals(id),
  scope_id uuid NOT NULL REFERENCES scopes(id),
  role text NOT NULL,
  valid_from timestamptz NOT NULL DEFAULT now(),
  valid_until timestamptz,
  PRIMARY KEY (principal_id, scope_id, role)
);

-- Seed slugs only. Display names stay TODO (D001–D003).
INSERT INTO principals (external_id, principal_type, display_name) VALUES
  ('employee-a', 'employee', 'TODO: legal name'),
  ('employee-b', 'employee', 'TODO: legal name'),
  ('employee-c', 'employee', 'TODO: legal name'),
  ('automation', 'service', '<Company> company automation'),
  ('company-system', 'system', 'Control-plane system');
