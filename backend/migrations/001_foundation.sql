-- Target PostgreSQL schema; not executed/validated against an engine yet.
BEGIN;
CREATE TABLE schema_migrations(version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE tenants(id uuid PRIMARY KEY, name text NOT NULL);
CREATE TABLE actors(
 tenant_id uuid NOT NULL REFERENCES tenants(id), id uuid NOT NULL,
 role text NOT NULL CHECK(role IN ('operator','approver','auditor','administrator','worker')),
 active boolean NOT NULL DEFAULT true, PRIMARY KEY(tenant_id,id));
CREATE TABLE deals(
 tenant_id uuid NOT NULL REFERENCES tenants(id), id text NOT NULL,
 version bigint NOT NULL CHECK(version>0), payload jsonb NOT NULL,
 PRIMARY KEY(tenant_id,id));
CREATE TABLE actor_deal_scope(
 tenant_id uuid NOT NULL, actor_id uuid NOT NULL, deal_id text NOT NULL,
 PRIMARY KEY(tenant_id,actor_id,deal_id),
 FOREIGN KEY(tenant_id,actor_id) REFERENCES actors(tenant_id,id),
 FOREIGN KEY(tenant_id,deal_id) REFERENCES deals(tenant_id,id));
CREATE TABLE sources(
 tenant_id uuid NOT NULL, id text NOT NULL, revision bigint NOT NULL CHECK(revision>0),
 deal_id text NOT NULL, payload jsonb NOT NULL, PRIMARY KEY(tenant_id,id),
 FOREIGN KEY(tenant_id,deal_id) REFERENCES deals(tenant_id,id));
CREATE TABLE proposals(
 tenant_id uuid NOT NULL, id uuid NOT NULL, deal_id text NOT NULL,
 actor_id uuid NOT NULL, payload jsonb NOT NULL, payload_hash char(64) NOT NULL,
 created_at timestamptz NOT NULL, expires_at timestamptz NOT NULL,
 version bigint NOT NULL CHECK(version>0), PRIMARY KEY(tenant_id,id),
 UNIQUE(tenant_id,deal_id,version),
 FOREIGN KEY(tenant_id,actor_id) REFERENCES actors(tenant_id,id),
 FOREIGN KEY(tenant_id,deal_id) REFERENCES deals(tenant_id,id));
CREATE INDEX proposals_hash ON proposals(tenant_id,payload_hash);
CREATE TABLE approvals(
 tenant_id uuid NOT NULL, proposal_id uuid NOT NULL,
 kind text NOT NULL CHECK(kind IN ('crm','email')), actor_id uuid NOT NULL,
 payload_hash char(64) NOT NULL, created_at timestamptz NOT NULL,
 PRIMARY KEY(tenant_id,proposal_id,kind),
 FOREIGN KEY(tenant_id,proposal_id) REFERENCES proposals(tenant_id,id),
 FOREIGN KEY(tenant_id,actor_id) REFERENCES actors(tenant_id,id));
CREATE TABLE operations(
 tenant_id uuid NOT NULL, id uuid NOT NULL, proposal_id uuid NOT NULL,
 kind text NOT NULL CHECK(kind IN ('crm','email')), idempotency_key uuid NOT NULL,
 status text NOT NULL CHECK(status IN ('prepared','approved','dispatched','accepted','verified','unknown','failed','review')),
 result jsonb, error_code text, created_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(tenant_id,id), UNIQUE(tenant_id,idempotency_key), UNIQUE(tenant_id,proposal_id,kind),
 FOREIGN KEY(tenant_id,proposal_id,kind) REFERENCES approvals(tenant_id,proposal_id,kind));
CREATE TABLE workflow_cursors(
 tenant_id uuid NOT NULL REFERENCES tenants(id), workflow text NOT NULL,
 cursor text, updated_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY(tenant_id,workflow));
CREATE TABLE audit_events(
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 tenant_id uuid NOT NULL, actor_id uuid NOT NULL, action text NOT NULL,
 resource_id text NOT NULL, at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY(tenant_id,actor_id) REFERENCES actors(tenant_id,id));
-- A non-owner runtime role must set app.tenant_id with SET LOCAL per transaction.
-- Provision roles separately and verify FORCE RLS/transactions under Phase 7.
DO $$ DECLARE tab text; BEGIN
 FOREACH tab IN ARRAY ARRAY['actors','deals','actor_deal_scope','sources','proposals','approvals','operations','workflow_cursors','audit_events'] LOOP
   EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY',tab);
   EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY',tab);
   EXECUTE format('CREATE POLICY tenant_scope ON %I USING (tenant_id = nullif(current_setting(''app.tenant_id'',true),'''')::uuid) WITH CHECK (tenant_id = nullif(current_setting(''app.tenant_id'',true),'''')::uuid)',tab);
 END LOOP;
END $$;
INSERT INTO schema_migrations(version) VALUES('001_foundation');
COMMIT;
