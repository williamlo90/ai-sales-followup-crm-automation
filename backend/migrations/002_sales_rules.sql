-- Static PostgreSQL target; engine execution remains Phase 7.
BEGIN;
ALTER TABLE operations ADD COLUMN effect_key char(64);
ALTER TABLE operations ADD COLUMN payload_hash char(64);
-- Existing operations require explicit backfill before tightening to NOT NULL.
CREATE UNIQUE INDEX operations_logical_effect ON operations(tenant_id,effect_key);
CREATE TABLE commitments(
 tenant_id uuid NOT NULL, deal_id text NOT NULL, id text NOT NULL,
 revision bigint NOT NULL CHECK(revision>0), payload jsonb NOT NULL,
 PRIMARY KEY(tenant_id,deal_id,id,revision),
 FOREIGN KEY(tenant_id,deal_id) REFERENCES deals(tenant_id,id));
ALTER TABLE commitments ENABLE ROW LEVEL SECURITY;
ALTER TABLE commitments FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_scope ON commitments
 USING(tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid)
 WITH CHECK(tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid);
INSERT INTO schema_migrations(version) VALUES('002_sales_rules');
COMMIT;
