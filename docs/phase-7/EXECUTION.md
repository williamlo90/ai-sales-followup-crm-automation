# Phase 7 execution checkpoint

Status: six real PostgreSQL migration/session probes passed under256MiB on2026-10-10. Application repository/composition and full Phase7A acceptance remain pending. Earlier inventory below is historical.

User authorized Phase7 after Phase6 completion. Initial Docker daemon unavailable, host RAM1.85GiB free. User freed RAM; recheck5,311,408KiB (~5.1GiB). Started Docker Desktop hidden; after startup three invoice-erpnext containers were observed running. They were not stopped or modified. Host free memory then1,462,352KiB and latest1,684,436KiB, below the4GiB pre-launch headroom gate. No sales container was launched. Port5444 was unoccupied; C: free460GB.

For the first database session: one PostgreSQL container only,512MiB/1CPU, loopback5444, dedicated database sales_phase7_acceptance, project-owned credentials and storage. No n8n/model/Odoo launch in this batch. Require4GiB free host RAM before launch; stop only the owned database if free RAM falls below1GiB or acceptance exceeds60seconds. Other projects are outside cleanup scope. Existing cached postgres17-bookworm digest is postgres@sha256:3645570cccdfa447589da9f57dd740faa29b30938e861289a5574b6ca6b03826; image ID589f742565e4f6d22149176b032974f55f8201a8a37b71ed587ec5c6902e689f. Original17.6 tag is not cached. Use an explicit isolated override if selecting the cached image; record actual server version before acceptance. No image pull performed.

Implemented backend/postgres_session.py: explicit tenant UUID, transaction-local context/timeouts, rejects superuser/BYPASSRLS runtime roles, rollback/close and no retries. This is not yet the application's repository; SQL/schema mappings and authenticated tenant/actor UUID mapping remain necessary. Added migration initialization advisory lock to prevent concurrent checksum-table initialization.

Driver psycopg/binary3.3.6 installed in project virtual environment and pinned in backend/requirements-postgres.txt. API semantics checked against [Psycopg transaction documentation](https://www.psycopg.org/psycopg3/docs/basic/transactions.html) and [PostgreSQL configuration functions](https://www.postgresql.org/docs/17/functions-admin.html). No secrets printed.

scripts/postgres_acceptance.py is ready for explicitly enabled execution against the dedicated database. It creates unique disposable schema/role, applies all7 migrations twice, checks missing-context read denial, two-tenant isolation, cross-tenant write denial, rollback/reconnect and checksum-drift rejection, then removes only its generated objects. This does not establish application, engine or connector acceptance. Script compiled and disabled execution refused as expected; it has not connected to PostgreSQL.

Validation:10 targeted contract tests passed (7 session,3 migration), existing Starlette warning only. These tests use doubles and do not prove server behavior. Next: restore sufficient RAM while Docker is running; run bounded real database probe, implement repository mapping using the existing business core, then test app persistence/concurrency and tenant isolation. Graph/Odoo sandbox configuration and eventual send authorization remain separate. Heartbeat remains paused.


## Authorized256MiB database session completed

User explicitly approved256MB and RAM monitoring without touching other containers. Used cached pinned PostgreSQL image above (actual17.11), one dedicated sales-phase7-pg256-20261010131415 container/database/volume and generated local credentials. Memory and memory-swap limits both268435456bytes,CPU0.5,pids64,shared_buffers32MB,work_mem1MB,maintenance_work_mem16MB,max_connections10. Stop threshold768MiB free host RAM, startup45s/probe60s deadlines. No image pull.

Six real checks passed: all7 migrations plus replay, unscoped runtime sees no rows, two-tenant read isolation, cross-tenant write denied, rollback/reconnect, changed migration checksum rejected. Actual database PostgreSQL17.11. Host RAM sampled minimum1,256,431,616bytes (~1.17GiB). Post-probe Docker usage55.7MiB/256MiB; not a measured peak. No OOM kill. Owned container stopped after probe. Three sibling ERPNext container IDs remained running unchanged. Dedicated stopped container/volume and secret remain local; no volume deletion. Evidence docs/evidence/phase-7-postgres-256mb.json; ignored raw runner local/phase7_pg256_run.py.

This supersedes the earlier4GiB launch gate for this bounded single-database probe only. It does not establish full-stack capacity. Next: implement explicit PostgreSQL repository/schema mapping and authenticated tenant/actor mapping, wire application, test persistence/approval/concurrency under real database. No complete Phase7A or end-to-end claim.
