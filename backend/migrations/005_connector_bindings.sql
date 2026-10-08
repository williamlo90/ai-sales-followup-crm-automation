BEGIN;
CREATE TABLE connector_bindings (
 tenant_id uuid NOT NULL, proposal_id uuid NOT NULL,
 connector_tenant uuid NOT NULL, connector_proposal uuid NOT NULL, payload jsonb NOT NULL,
 PRIMARY KEY(tenant_id,proposal_id), UNIQUE(connector_tenant,connector_proposal),
 FOREIGN KEY(tenant_id,proposal_id) REFERENCES proposals(tenant_id,id));
ALTER TABLE connector_bindings ENABLE ROW LEVEL SECURITY;
ALTER TABLE connector_bindings FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_scope ON connector_bindings
 USING(tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid)
 WITH CHECK(tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid);
INSERT INTO schema_migrations(version) VALUES('005_connector_bindings');
COMMIT;
