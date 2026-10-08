# Phase 0–6 execution checkpoint

## Mandate

Implement Phase 0 through Phase 6 efficiently and accurately, following PHASES.md and ../LOCAL-FIRST-EXECUTION.md. Continue from evidence on disk each run. Phase 7–9 execution is outside this loop.

## Current status

- Phase 0: scope/audit/mapping and initial labeled fixture corpora are recorded. Final gate review must confirm the documented pending access and budgets; no external access is claimed validated.
- Phase 1: in progress; FastAPI domain, durable SQLite harness, server-owned token/tenant/deal roles, proposal versions, separate approvals, React review UI and static PostgreSQL/deploy artifacts implemented. Adapter doubles, PostgreSQL wiring/migration runner and final gate review remain.
- Phase 2: scoped matching, candidate commitment history/merge, due eligibility, durable operation dispatch/reconciliation core and contract-double effect deduplication implemented. Bind reviewed commitment revisions to proposals, complete effect/update policy and API/UI recovery before closing gate.
- Phase 3–6: pending.
- Project 04 now has its own Git repository, Python venv, pinned dependency locks and implementation. Sibling projects were inspected read-only.
- No phase gates have been marked passed.

## Initial verified findings

- Project 02 contains a real implementation. Observed HEAD: `6a55b9dc61acd87e61b3aacb4da97d61af84b0fa`; working tree was clean at audit.
- `../02 - Odoo Business Operations MCP Server/backend/contracts.py` exposes contract version 1.0: ActivityPreview, ProposalOut, ApprovalOut, ActivityRecord, Receipt and OperationOut.
- Activity preview includes company, opportunity, assignee, due date, summary and source version. Approval binds proposal and payload hash. Operation status distinguishes dispatched, unknown, verified, failed and review.
- Arbitrary CRM field updates are not established by that initial contract inspection. Audit actual API/adapter support and document any gap before designing a consumer extension.
- Microsoft 365/model credentials have not been supplied to this project. User says they should exist; ask for concrete authorized config locations when bounded live tests are ready, never secret values in chat. No relevant shell environment-variable names were found. Hardware/version observations and native Ollama PATH absence are in docs/phase-0/DEPENDENCIES.md.

## Next executable work

1. Review Phase 0 gate using docs/phase-0/ and fixtures/rules-v1.json + fixtures/conversations-v1.json. External credentials are pending config location, not assumed unavailable. Model spend defaults to zero until an authorized profile/budget is configured.
2. Finish Phase 1 PostgreSQL repository/migration runner preparation and security/config gaps; real PostgreSQL checks remain Phase 7. Preserve one business core. An effect contract double and persistent operation ledger now exist.
3. Phase 2: bind candidate commitments to reviewed proposals, handle multiple commitments/changed-revision activity updates, expose authenticated operation read/recovery states with safe adapter configuration, and add remaining failure cases. Dispatch core remains tests-only: do not enable fake execution in the normal UI and call it a connected result.
4. Then proceed Phase 3–6 according to PHASES.md. Do not stop independent coding for missing provider credentials.

## Latest verification

2026-10-09 Asia/Jakarta: 58 Python tests passed and Edge browser regression passed after rules/API changes. Earlier TypeScript/Vite build and pip dependency check passed. See docs/evidence/sales-rules-checks.md and foundation-checks.md. No live external dispatch exists. Upstream Starlette warns HTTPX TestClient is deprecated; tests still pass; resolve dependency compatibility before final freeze.

Native commands: `.venv/Scripts/python.exe -m pytest -q`; `npm.cmd run build --prefix web`; `npm.cmd run test:e2e --prefix web`. Browser test uses installed Edge (channel msedge), creates temporary fixture data, starts its own servers on 8040/8044 and refuses existing servers. Npm scripts invoke Node entry files directly to avoid Windows shim failures with `&` in the project path. See docs/LOCAL-DEVELOPMENT.md.

Automation: `sales-automation-phase-0-6`, active heartbeat every five minutes in this chat. Continue substantive implementation each run; this checkpoint is not the finished project.

## Per-run checkpoint

Record changed artifacts, exact check commands and results, evidence paths, unresolved dependencies, and the next executable step. Check PHASES.md items only when their evidence exists. Keep implemented, contract-validated, native-model-validated and connected-validated statuses distinct.

Continue independent work when an external dependency is pending. Do not label a phase fully passed while its required real-provider or local-model gate remains unmet. Do not repeatedly retry an unchanged credential/resource blocker.

## Completion

After Phase 0–6 gates pass, freeze the candidate, prepare the Phase 7 acceptance handoff and deactivate this loop. If all remaining work requires unavailable external input, record precise unblock requirements, report once and suspend this loop until resumed. Do not proceed into Docker execution, cloud provisioning or sending email.
