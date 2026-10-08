# Phase 0–6 execution checkpoint

## Mandate

Implement Phase 0 through Phase 6 efficiently and accurately, following PHASES.md and ../LOCAL-FIRST-EXECUTION.md. Continue from evidence on disk each run. Phase 7–9 execution is outside this loop.

## Current status

- Phase 0: scope/audit/mapping and initial labeled fixture corpora are recorded. Final gate review must confirm the documented pending access and budgets; no external access is claimed validated.
- Phase 1: in progress; foundation implemented, migration plan/runner contract tests added. PostgreSQL runtime wiring, session/config hardening and final gate review remain; no engine acceptance yet.
- Phase 2: commitments bound to proposals, revision/cancellation invalidation, operation-read API and recovery UI added. Effect/update policy and safe connected adapter wiring remain before closing gate.
- Phase 3: four shared application skills and OpenAI/Claude/Grok/Ollama structured adapters implemented and contract-tested. Safe OpenAI config loading and one real synthetic canary now pass through extraction, proposal and draft. Other provider/native inference, full nested output schemas, quality/security evaluation and multi-caller reuse remain.
- Phase 4–6: pending.
- Project 04 now has its own Git repository, Python venv, pinned dependency locks and implementation. Sibling projects were inspected read-only.
- No phase gates have been marked passed.

## Initial verified findings

- Project 02 contains a real implementation. Observed HEAD: `6a55b9dc61acd87e61b3aacb4da97d61af84b0fa`; working tree was clean at audit.
- `../02 - Odoo Business Operations MCP Server/backend/contracts.py` exposes contract version 1.0: ActivityPreview, ProposalOut, ApprovalOut, ActivityRecord, Receipt and OperationOut.
- Activity preview includes company, opportunity, assignee, due date, summary and source version. Approval binds proposal and payload hash. Operation status distinguishes dispatched, unknown, verified, failed and review.
- Arbitrary CRM field updates are not established by that initial contract inspection. Audit actual API/adapter support and document any gap before designing a consumer extension.
- OpenAI key supplied in the project-local ignored .env and validated by one real synthetic request. Microsoft 365, Claude/Grok and dedicated Odoo test access remain pending concrete authorized configuration; never request secret values in chat. Hardware/version observations and native Ollama PATH absence are in docs/phase-0/DEPENDENCIES.md.

## Next executable work

1. Review Phase 0 gate using docs/phase-0/ and fixtures/rules-v1.json + fixtures/conversations-v1.json. External credentials are pending config location, not assumed unavailable. OpenAI one-request synthetic budget was used successfully; do not repeat it automatically or start bulk evaluations without a defined budget.
2. Finish Phase 1 PostgreSQL repository/migration runner preparation and security/config gaps; real PostgreSQL checks remain Phase 7. Preserve one business core. An effect contract double and persistent operation ledger now exist.
3. Phase 2: close manual-vs-bound proposal effect identity overlap and multiple-commitment/update policy; expose recovery actions only with a safe configured adapter. Bound revisions after an existing action currently require review, because connector #2 update capability is absent. Dispatch remains tests-only; no fake-connected UI.
4. Phase 3: safe .env loading and the bounded synthetic OpenAI canary are complete. The app stays model-disabled; the canary explicitly uses one request with a persistent reservation. Do not rerun/reset local/openai-canary.json automatically. Next: complete nested skill output schemas and implement the MCP stdio bridge/reference client, then workflow and adapter contracts. Remaining provider/local acceptance and evaluation budget are pending; continue independent work. Model snapshot used for canary is not yet the final default selection.

## Latest verification

2026-10-09 Asia/Jakarta: 105 Python tests passed after configuration/canary changes. Previous unchanged UI: TypeScript/Vite build and two Edge browser scenarios passed. See docs/evidence/skills-providers-checks.md for actual scope and pending gates. One real OpenAI request passed (551 tokens, 3345.69 ms; estimated USD 0.0003812); see docs/evidence/openai-canary.md. No live Graph/Odoo action exists. Upstream Starlette warns HTTPX TestClient is deprecated; tests still pass; resolve dependency compatibility before final freeze.

Native commands: `.venv/Scripts/python.exe -m pytest -q`; `npm.cmd run build --prefix web`; `npm.cmd run test:e2e --prefix web`. Browser test uses installed Edge (channel msedge), creates temporary fixture data, starts its own servers on 8040/8044 and refuses existing servers. Npm scripts invoke Node entry files directly to avoid Windows shim failures with `&` in the project path. See docs/LOCAL-DEVELOPMENT.md.

Automation: `sales-automation-phase-0-6`, active heartbeat every five minutes in this chat. Continue substantive implementation each run; this checkpoint is not the finished project.

## Per-run checkpoint

Record changed artifacts, exact check commands and results, evidence paths, unresolved dependencies, and the next executable step. Check PHASES.md items only when their evidence exists. Keep implemented, contract-validated, native-model-validated and connected-validated statuses distinct.

Continue independent work when an external dependency is pending. Do not label a phase fully passed while its required real-provider or local-model gate remains unmet. Do not repeatedly retry an unchanged credential/resource blocker.

## Completion

After Phase 0–6 gates pass, freeze the candidate, prepare the Phase 7 acceptance handoff and deactivate this loop. If all remaining work requires unavailable external input, record precise unblock requirements, report once and suspend this loop until resumed. Do not proceed into Docker execution, cloud provisioning or sending email.

## Latest batch — OpenAI access and native canary

Artifacts: backend/config.py, app factory wiring, secret-safe ModelProfile repr, scripts/model_canary.py, pinned python-dotenv dependency, config/canary regression tests and operator documentation. Commands: `.venv/Scripts/python.exe -m pytest -q` → 105 passed; `.venv/Scripts/python.exe -m scripts.model_canary --run` → passed once. Source/owner/due/revision validation and the shared local proposal/draft slice succeeded. Canary repeat protection and rejection of wrong owner are tested without network. Existing TestClient deprecation warning remains. Evidence: docs/evidence/openai-canary.md and ignored local/openai-canary.json. No phase gate changed. Next executable batch: skill output contracts and actual MCP stdio/reference client.
