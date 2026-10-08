BEGIN;
CREATE TABLE model_runs(
 tenant_id uuid NOT NULL, id uuid NOT NULL, actor_id uuid NOT NULL,
 deal_id text NOT NULL, metadata jsonb NOT NULL,
 PRIMARY KEY(tenant_id,id),
 FOREIGN KEY(tenant_id,actor_id) REFERENCES actors(tenant_id,id),
 FOREIGN KEY(tenant_id,deal_id) REFERENCES deals(tenant_id,id));
ALTER TABLE model_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE model_runs FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_scope ON model_runs
 USING(tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid)
 WITH CHECK(tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid);
INSERT INTO schema_migrations(version) VALUES('003_model_runs');
COMMIT;
