-- Static target only. Apply/test with PostgreSQL in the Phase 7 data session.
BEGIN;
CREATE TABLE ingestion_streams (
 tenant_id uuid NOT NULL REFERENCES tenants(id), stream text NOT NULL,
 generation bigint NOT NULL CHECK(generation>0), checkpoint jsonb NOT NULL,
 PRIMARY KEY(tenant_id,stream));
CREATE TABLE ingestion_messages (
 tenant_id uuid NOT NULL, stream text NOT NULL, external_id text NOT NULL,
 source_id text NOT NULL, deal_id text NOT NULL, change_key text,
 modified_at timestamptz, deleted boolean NOT NULL, content_hash char(64) NOT NULL,
 PRIMARY KEY(tenant_id,stream,external_id),
 FOREIGN KEY(tenant_id,source_id) REFERENCES sources(tenant_id,id),
 FOREIGN KEY(tenant_id,deal_id) REFERENCES deals(tenant_id,id));
ALTER TABLE ingestion_streams ENABLE ROW LEVEL SECURITY;
ALTER TABLE ingestion_streams FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_scope ON ingestion_streams
 USING(tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid)
 WITH CHECK(tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid);
ALTER TABLE ingestion_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE ingestion_messages FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_scope ON ingestion_messages
 USING(tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid)
 WITH CHECK(tenant_id=nullif(current_setting('app.tenant_id',true),'')::uuid);
INSERT INTO schema_migrations(version) VALUES('004_ingestion');
COMMIT;
