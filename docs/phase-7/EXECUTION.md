# Phase 7 execution checkpoint

Status: six real PostgreSQL migration/session probes passed under256MiB on2026-10-10. Application PostgreSQL wiring and focused approval/concurrency checks subsequently passed; full Phase7A remains pending. Earlier inventory below is historical.

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


## Application PostgreSQL wiring and focused acceptance

Added PostgresStore and explicit SALES_STORAGE=postgresql app-factory configuration, preserving one shared domain implementation. All business callers now pass authenticated actor to transaction boundary. Explicit column/type/placeholder mapping, database actor active/role check, tenant-local RLS context and per-tenant advisory transaction lock support durable read-before-write decisions. No model/effect enabled. Runtime instructions in POSTGRES-RUNTIME.md.

Real test in fresh isolated256MiB container passed12 combined checks.8 concurrent prepare requests ->1 proposal and1 audit;8 concurrent CRM approval requests ->1 approval and1 audit. Operator approval/cross-tenant reads denied; fresh interpreter reconstructed app and read durable approval; source revision invalidated old approval; zero operations. Actual PostgreSQL17.11; ASGI transport, not deployed HTTP load. Evidence phase-7-postgres-app-256mb.json. Container post-probe25.71MiB (not peak); host minimum sampled1,693,265,920bytes (~1.58GiB), no OOM. Owned container stopped; same three sibling IDs remain running. Test schema/role cleaned up, dedicated stopped container/volume retained.


## Database restart and workflow persistence verified

Extended application probe to intake/due discovery, duplicate enqueue/cursor replay, concurrent worker claims and controlled real container restart. Restart checks exact container ID, ownership label and256MiB memory limit; postmaster start timestamp must increase.15 combined real checks passed;14 targeted native tests passed0.74s. Saved approval/job state and next_at survive restart; lease is released; polling does not double-prepare. No business effects. Evidence phase-7-postgres-workflow-restart.json. Minimum sampled free host RAM3,025,039,360bytes (~2.82GiB), post-probe13.56MiB/256MiB, no OOM. Owned container stopped after probe; sibling container IDs unchanged. Controlled restart is not abrupt crash/host reboot, Python workflow is not n8n acceptance. Next: broader execution/ingestion on PostgreSQL and connector composition before real sandbox/engine tests.


## Ingestion/ledger and connector composition

19 combined checks passed on real PostgreSQL256MiB. Added atomic rollback of invalid Graph page, persistent checkpoint/replay without source inflation,8 concurrent execution calls yielding1 ledger row/1 simulated dispatch, unknown-result read-back without redispatch. Graph/effect adapters are doubles: no vendor integration or real writes. Minimum sampled free RAM2,772,680,704bytes (~2.58GiB), post-probe13.61MiB/256MiB, no OOM; owned container stopped, same3 sibling IDs running. Evidence phase-7-postgres-ingestion-execution.json.

Explicit project-local connector JSON composes Odoo/Graph/router/ingestion into app factory. Strict worker/tenant/deal mapping and local token-file paths; one-page authenticated Graph poll endpoint; Odoo tenant boundary. Runtime effects remain disabled with no enabling config flag.7 composition tests passed0.63s; prior full suite289 passed11s before adding those tests. Setup docs/phase-7/CONNECTOR-SETUP.md and deploy/connectors.example.json. Next requires authorized project sandbox configuration for bounded real read-only connector tests; no credentials borrowed.
