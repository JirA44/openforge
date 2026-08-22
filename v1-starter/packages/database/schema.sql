CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TYPE strategy_status AS ENUM (
  'DRAFT','RESEARCH','BACKTESTING','BACKTEST_VALIDATED','OOS_VALIDATED',
  'PAPER_VALIDATED','SHADOW_VALIDATED','CERTIFIED','READY_FOR_LIVE',
  'LIVE','SUSPENDED','DECERTIFIED'
);

CREATE TABLE projects (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id text NOT NULL,
  name text NOT NULL,
  visibility text NOT NULL DEFAULT 'private',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE strategies (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid NOT NULL REFERENCES projects(id),
  name text NOT NULL,
  thesis text NOT NULL,
  market text NOT NULL,
  venue text NOT NULL,
  timeframe text NOT NULL,
  status strategy_status NOT NULL DEFAULT 'DRAFT',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE strategy_versions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  strategy_id uuid NOT NULL REFERENCES strategies(id),
  version text NOT NULL,
  code_hash char(64) NOT NULL,
  config_hash char(64) NOT NULL,
  parent_id uuid REFERENCES strategy_versions(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(strategy_id, version)
);

CREATE TABLE dataset_versions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source text NOT NULL,
  range_start timestamptz NOT NULL,
  range_end timestamptz NOT NULL,
  schema_hash char(64) NOT NULL,
  content_hash char(64) NOT NULL UNIQUE,
  quality jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE experiment_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  strategy_version_id uuid NOT NULL REFERENCES strategy_versions(id),
  dataset_version_id uuid NOT NULL REFERENCES dataset_versions(id),
  runner_image text NOT NULL,
  manifest_hash char(64) NOT NULL UNIQUE,
  status text NOT NULL,
  metrics jsonb,
  logs_uri text,
  created_at timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz
);

CREATE TABLE certifications (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  strategy_version_id uuid NOT NULL REFERENCES strategy_versions(id),
  policy_version text NOT NULL,
  decision text NOT NULL CHECK (decision IN ('PASS','FAIL')),
  evidence_set_hash char(64) NOT NULL,
  reasons jsonb NOT NULL,
  score numeric(5,2) NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE deployments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  strategy_version_id uuid NOT NULL REFERENCES strategy_versions(id),
  mode text NOT NULL CHECK (mode IN ('paper','shadow','live')),
  venue text NOT NULL,
  capital_limit numeric NOT NULL CHECK (capital_limit >= 0),
  active boolean NOT NULL DEFAULT false,
  approved_by text,
  approved_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE audit_events (
  id bigserial PRIMARY KEY,
  event_type text NOT NULL,
  actor_id text NOT NULL,
  entity_type text NOT NULL,
  entity_id text NOT NULL,
  payload jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_strategy_status ON strategies(status);
CREATE INDEX idx_runs_strategy_version ON experiment_runs(strategy_version_id);
CREATE INDEX idx_certifications_version ON certifications(strategy_version_id, created_at DESC);
CREATE INDEX idx_audit_entity ON audit_events(entity_type, entity_id, created_at DESC);

