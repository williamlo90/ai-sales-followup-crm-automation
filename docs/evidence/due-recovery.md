# Due discovery and recovery

The due tick now scans latest commitment revisions in bounded pages with a persisted worker cursor. It skips future, cancelled, opted-out, deleted and out-of-scope records and idempotently queues due email work. Enqueue happens before cursor advancement, so interruption replays existing jobs instead of losing candidates. PostgreSQL migration 007 prepares scan cursor storage; actual engine behavior remains unverified.

A future due job does not prepare a proposal early and consume its approval lifetime. Proposal preparation starts when the commitment is due. Intake email still checks due eligibility before execution. The scanner queues candidates for human proposal approval; discovery does not grant approval or assert that extraction was human-validated.

`GET /v1/workflows/jobs` provides a scoped bounded recovery list. `POST /v1/workflows/jobs/{id}/recover` accepts three explicit actions: `observe` keeps the existing operation; `renew_expired` clears only an expired proposal reference when no operation exists; `recheck` requeues prerequisites only when no operation exists. Active leases, read-only roles and cross-tenant requests are rejected. Renewed proposals get new IDs and no inherited approvals. Recovery never calls an external adapter directly.

The workspace now shows jobs and these recovery controls. The new Edge scenario verifies that the observation button sends the observation action and updates status, using mocked job presentation responses. Python tests separately validate actual recovery authorization and state changes. Existing browser preparation/approval scenarios still use the real local fixture backend.

Validation on 2026-10-09 Asia/Jakarta: Python suite 207 passed; TypeScript/Vite build passed; three Edge scenarios passed. Existing Starlette TestClient deprecation warning remains. No provider call, actual send, Odoo mutation, n8n engine or container was run.

Remaining: automatic intake extraction/candidate handoff, connector binding/preparation UI, explicit source mapping/restoration workflows, PostgreSQL wiring and live access/evaluation gates. Concurrent cursor updates may repeat a scan page; deterministic enqueue prevents duplicate jobs and each scan cycle revisits the dataset. This is native SQLite evidence, not proof of PostgreSQL scheduling concurrency.
