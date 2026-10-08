BEGIN;
CREATE TABLE workflow_scans (
 tenant_id uuid NOT NULL, worker_id uuid NOT NULL, kind text NOT NULL CHECK(kind IN ('crm','email')),
 cursor jsonb NOT NULL, PRIMARY KEY(tenant_id,worker_id,kind),
 FOREIGN KEY(tenant_id,worker_id) REFERENCES actors(tenant_id,id));
ALTER TABLE workflow_scans ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflow_scans FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_scope ON workflow_scans
 USING(tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid)
 WITH CHECK(tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid);
INSERT INTO schema_migrations(version) VALUES('007_workflow_scans');
COMMIT;
