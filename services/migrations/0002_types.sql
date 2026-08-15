-- 0002_types.sql
-- Spec 14.3, 24.2, 28.1; governance data-classification-retention.md

CREATE TYPE data_classification AS ENUM
  ('public', 'internal', 'confidential', 'restricted');

CREATE TYPE document_state AS ENUM
  ('inbox', 'indexed', 'reviewed', 'curated', 'superseded', 'quarantined', 'deleted');

CREATE TYPE visibility_scope AS ENUM
  ('private', 'team', 'project', 'company', 'public');

CREATE TYPE source_status AS ENUM
  ('quarantined', 'active', 'superseded', 'deleted', 'legal_hold');

CREATE TYPE claim_status AS ENUM
  ('candidate', 'verified', 'disputed', 'superseded', 'rejected');

CREATE TYPE principal_type AS ENUM
  ('employee', 'service', 'system');
