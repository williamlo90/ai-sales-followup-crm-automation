BEGIN;
CREATE TABLE workflow_jobs (
 tenant_id uuid NOT NULL, id text NOT NULL, worker_id uuid NOT NULL, deal_id text NOT NULL,
 journey text NOT NULL CHECK(journey IN ('intake','due')), payload jsonb NOT NULL,
 status text NOT NULL, proposal_id uuid, operation_id uuid, next_at timestamptz NOT NULL,
 lease_id uuid, lease_until timestamptz, error_code text,
 PRIMARY KEY(tenant_id,id), FOREIGN KEY(tenant_id,deal_id) REFERENCES deals(tenant_id,id),
 FOREIGN KEY(tenant_id,worker_id) REFERENCES actors(tenant_id,id));
CREATE INDEX workflow_due ON workflow_jobs(tenant_id,worker_id,journey,next_at);
ALTER TABLE workflow_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflow_jobs FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_scope ON workflow_jobs
 USING(tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid)
 WITH CHECK(tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid);
INSERT INTO schema_migrations(version) VALUES('006_workflows');
COMMIT;
