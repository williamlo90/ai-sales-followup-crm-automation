# Phase 5 — native workflow and workspace acceptance

Verified 2026-10-10. Status: workflow-designed / contract-validated. This is the Phase 5 native gate specified in PHASES.md, not n8n-validated or a connected release.

| Requirement | Current artifact and evidence |
| --- | --- |
| Two versioned intake/due workflows | automation/n8n/intake-v1.json and due-v1.json; generator parity, static node contracts, intake approval-to-completion and due discovery-to-accepted-effect traversal in tests/test_workflow_exports.py |
| One business implementation; domain owns state | backend/workflows.py delegates to SalesService, SkillService and ExecutionService. Nodes only schedule, request, branch on needs_poll and wait. Durable local harness; target PostgreSQL tables/RLS in migrations 001–007. Runtime PostgreSQL wiring is an earlier-phase prerequisite still pending, not proven by these tests. |
| Authenticated outbound polling | worker-only tick routes; digest-authenticated server-owned tenant/deal scopes; no webhook. test_workflows.py checks unauthorized and wrong-tenant callers. |
| Mapping, identities, placeholders, time and recovery | phase-0/N8N-MAPPING.md, automation/n8n/README.md and deploy/compose.yaml; placeholder credential, Jakarta schedule, max two requests, 240-second timeout, no POST retry, cursor/lease/operation ledger. Engine concurrency/retention/encryption config is static only. |
| Export/endpoint reference checks | test_workflow_exports.py runs actual FastAPI/domain with effect doubles and simulated waits. No duplicate business engine. Both success and not-due/idle branches verified. |
| Workspace evidence/diff/approvals/outcomes/recovery | main.tsx, IntakeReview, ConnectorBinding, ProposalHandoff and WorkflowQueue. Mapped new-activity field table uses shared adapter rules and scoped opportunity GET; separate approvals and conservative unknown outcomes. Six Edge tests cover review, extraction-to-handoff, ambiguity, binding preview/error/success, unknown status and recovery. |
| Intake handoff | test_handoff.py: owner, role, scope, stale-source rejection, replay and separate kinds. test_preparation.py: zero/multiple worker configuration fails closed. Reviewed proposal ID is retained. |
| Odoo preparation and binding | shared expected_activity function; repository freshness recheck after GET. Binding API uses only connector reads, validates approval/preview and persists immutable association. tests/test_bindings.py and test_preparation.py. Remote proposal preparation/approval uses existing #2 workspace; no second connector implementation. |
| Renewal/restart | test_workflow_recovery.py and test_workflows.py: new proposal/new approval on expiry, observation-only unknown recovery, lost job-checkpoint restart and concurrent claim. Renewed proposals belong to worker; binding controls support operator/worker, while backend requires the actual proposer identity. No ownership bypass. |

## Commands and outcomes

- `.venv/Scripts/python.exe -m pytest -q`: 220 passed; existing Starlette HTTPX TestClient deprecation warning.
- `npm run build` in web: TypeScript and Vite passed.
- `npm run test:e2e` in web: six Edge scenarios passed.
- `git diff --check`: passed.

Browser model and connector responses are mocked; intake recording/preparation/handoff use the actual local backend. Python effect/read-client tests use network boundary doubles. No new hosted-model run, Graph/Odoo connected call, email, Docker or engine session occurred.

## Before connected acceptance

The normal application factory remains disconnected with sending off. Complete earlier-phase PostgreSQL runtime wiring and connector/identity configuration before a real engine session; the compose template intentionally does not pretend those are ready. Configure one scoped worker per tenant/deal for operator handoff. Native tests do not establish PostgreSQL locking/RLS, n8n import/wait/restart, OAuth behavior or real platform side effects. Those integrations require their declared Phase 7 acceptance. Phase 0–4 and Phase 6 are not closed by this report.

The heartbeat automation remains PAUSED. Phase 5 completion is limited to its declared native definitions, endpoints and workspace gate; it is not permission to start Phase 7.
