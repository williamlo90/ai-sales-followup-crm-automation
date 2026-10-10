# Phase 0–6 execution checkpoint

## Mandate

Implement Phase 0 through Phase 6 efficiently and accurately, following PHASES.md and ../LOCAL-FIRST-EXECUTION.md. Continue from evidence on disk each run. Phase 7–9 execution is outside this loop.

## Current status

- Phase 0: scope/audit/mapping and initial labeled fixture corpora are recorded. Final gate review must confirm the documented pending access and budgets; no external access is claimed validated.
- Phase 1: in progress; foundation implemented, migration plan/runner contract tests added. PostgreSQL runtime wiring, session/config hardening and final gate review remain; no engine acceptance yet.
- Phase 2: commitments bound to proposals, revision/cancellation invalidation, operation-read API and recovery UI added. Manual/bound overlap and alias evidence checks now protect dispatch and due checks. Full effect/update review policy and safe connected adapter wiring remain before closing gate.
- Phase 3: four shared application skills and OpenAI/Claude/Grok/Ollama structured adapters implemented and contract-tested. Safe OpenAI config loading and one real synthetic canary now pass through extraction, proposal and draft. Complete nested output schemas and actual MCP-to-API reuse now pass. Other provider/native inference, quality/security evaluation and workflow reuse remain.
- Phase 4: native MCP bridge/reference client implemented and protocol-tested against the shared backend; Read-only Graph/Odoo clients now have bounded scope/pagination/retry contract tests. Atomic Graph ingestion/checkpoint core now passes native tests. Odoo activity dispatch/read-back adapter now contract-tested but disabled; Graph send/read-back adapter and effect router also contract-tested. Immutable connector binding storage and default-off review API now pass tests. Connector proposal creation, scheduler activation and mapping/recovery UI remain. Phase 5 has durable coordinator and two inactive n8n exports with endpoint-contract tests; upstream intake/due discovery, recovery UI and engine gates remain. Phase 6 pending.
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
3. Phase 2: manual-vs-bound effect overlap is covered, including concurrency and unknown outcomes. Finish multiple-commitment/update review policy; expose recovery actions only with a safe configured adapter. Bound revisions after an existing action currently require review, because connector #2 update capability is absent. Dispatch remains tests-only; no fake-connected UI.
4. Phase 3: safe .env loading and the bounded synthetic OpenAI canary are complete. The app stays model-disabled; the canary explicitly uses one request with a persistent reservation. Do not rerun/reset local/openai-canary.json automatically. Nested skill outputs and the native MCP bridge/reference client are now validated. Next: Graph/Odoo business clients, deeper protocol failures, then workflow contracts. Remaining provider/local acceptance and evaluation budget are pending; continue independent work. Model snapshot used for canary is not yet the final default selection.

## Latest verification

2026-10-09 Asia/Jakarta: 207 Python tests passed; MCP TypeScript build and two native protocol suites passed after effect-overlap/read-client changes. TypeScript/Vite build and three Edge browser scenarios passed after adding workflow recovery UI. See docs/evidence/skills-providers-checks.md for actual scope and pending gates. One real OpenAI request passed (551 tokens, 3345.69 ms; estimated USD 0.0003812); see docs/evidence/openai-canary.md. No live Graph/Odoo action exists. Upstream Starlette warns HTTPX TestClient is deprecated; tests still pass; resolve dependency compatibility before final freeze.

Native commands: `.venv/Scripts/python.exe -m pytest -q`; `npm.cmd run build --prefix web`; `npm.cmd run test:e2e --prefix web`. Browser test uses installed Edge (channel msedge), creates temporary fixture data, starts its own servers on 8040/8044 and refuses existing servers. Npm scripts invoke Node entry files directly to avoid Windows shim failures with `&` in the project path. See docs/LOCAL-DEVELOPMENT.md.

Automation: `sales-automation-phase-0-6`, active heartbeat every five minutes in this chat. Continue substantive implementation each run; this checkpoint is not the finished project.

## Per-run checkpoint

Record changed artifacts, exact check commands and results, evidence paths, unresolved dependencies, and the next executable step. Check PHASES.md items only when their evidence exists. Keep implemented, contract-validated, native-model-validated and connected-validated statuses distinct.

Continue independent work when an external dependency is pending. Do not label a phase fully passed while its required real-provider or local-model gate remains unmet. Do not repeatedly retry an unchanged credential/resource blocker.

## Completion

After Phase 0–6 gates pass, freeze the candidate, prepare the Phase 7 acceptance handoff and deactivate this loop. If all remaining work requires unavailable external input, record precise unblock requirements, report once and suspend this loop until resumed. Do not proceed into Docker execution, cloud provisioning or sending email.

## Latest batch — OpenAI access and native canary

Artifacts: backend/config.py, app factory wiring, secret-safe ModelProfile repr, scripts/model_canary.py, pinned python-dotenv dependency, config/canary regression tests and operator documentation. Commands: `.venv/Scripts/python.exe -m pytest -q` → 105 passed; `.venv/Scripts/python.exe -m scripts.model_canary --run` → passed once. Source/owner/due/revision validation and the shared local proposal/draft slice succeeded. Canary repeat protection and rejection of wrong owner are tested without network. Existing TestClient deprecation warning remains. Evidence: docs/evidence/openai-canary.md and ignored local/openai-canary.json. No phase gate changed. Next executable batch: skill output contracts and actual MCP stdio/reference client.

## Latest batch — native MCP and output contracts

Artifacts: backend/skill_outputs.py, runtime skill output validation, scoped context and disabled-by-default execution API routes, mcp-server TypeScript bridge/reference client/lock/schemas/tests, scripts/mcp_fixture.py, exported skill schemas and API regression tests. Commands/results: Python pytest → 107 passed; MCP build → passed; native MCP tests → 2 passed; git diff --check → clean. Evidence: docs/evidence/mcp-native.md. No paid canary repeated. Protocol target now 2026-07-28 with SDK 2.3.1. No approval MCP tool. Current app factory still cannot dispatch external effects. Next: close Phase 2 manual/bound effect overlap before any connected dispatch; build Odoo #2/Graph clients and workflow contracts. External access/evaluation budget dependencies unchanged.

## Latest batch — overlap guard and read-only clients

Artifacts: SalesService.prior_effect shared by execution/eligibility, backend/read_clients.py, overlap/concurrency and HTTP contract tests, MCP error mapping. Commands: pytest → 132 passed; MCP build → passed; MCP stdio suites → 2 passed. Evidence: docs/evidence/effects-read-clients.md. Read clients are implemented/contract-validated only, not live-validated or scheduler-wired. Odoo collection cap/pagination gap confirmed from #2 read-only source. Next: transactional source/checkpoint ingestion, explicit external-to-local identity mapping, Odoo approval/operation binding and Graph reconciliation contracts, then two n8n exports/reference runner. OpenAI canary reservation unchanged; no paid calls or connected writes. No phase gate newly closed.

## Latest batch — atomic Graph ingestion

Artifacts: backend/ingestion.py, shared transactional source-ingestion helper, deleted source contracts/guards, SQLite ingestion ledger/checkpoints, static PostgreSQL migration 004, updated MCP context schema and tests/test_ingestion.py. Source identity binds mailbox/immutable message ID. Checkpoint generation compare plus atomic rollback prevents lost pages; explicit mapping blocks ambiguity. Tombstones invalidate old evidence and are excluded from model source input.

Commands/results: pytest → 145 passed; migration dry plan → four SQL files, no DB execution; schema exporter → updated; native MCP suites → 2 passed. One migration-plan expectation required updating for migration 004; final suite passes. Evidence: docs/evidence/ingestion-checkpoints.md. No external calls or paid canary repeated.

Next: Odoo #2 proposal/approval/operation binding and Graph draft/send/reconciliation contracts, then scheduler endpoint/queue and two n8n exports. Graph ingestion poll is an internal worker API, not yet exposed/activated. Message mapping, folder-move recovery, resync/review interface, test credentials and real PostgreSQL wiring remain. No complete phase gate changed; automation remains active.

## Latest batch — Odoo activity execution boundary

Artifacts: backend/odoo_effects.py, tests/test_odoo_effects.py, pinned tzdata 2026.5 and docs/evidence/odoo-effect-contract.md. Reuses #2 workspace/proposal/execute/read-back contracts. Checks local hash binding, connector tenant/operator/approval, activity fields, timezone date and full receipt. Lost-response observation does not redispatch. Write switch defaults off; normal app factory remains disconnected.

Validation: pytest → 163 passed (18 Odoo effect contract cases added). Initial Windows tests exposed missing IANA timezone data; dependency is now pinned and those cases pass. Existing Starlette warning remains. git diff --check passes. No external calls, model spend, Docker or connected writes.

Next executable work: persistent immutable connector bindings and proposal preparation workflow; Graph draft/send/read-back adapter with conservative unknown-outcome handling; scheduler queue/API and n8n definitions. Binding provider and deal/company mapping are injected contracts, not yet a connected setup flow. Continue independent implementation; no phase gate closed and automation remains active.

## Latest batch — Graph mail effect boundary

Artifacts: backend/graph_effects.py, tests/test_graph_effects.py and docs/evidence/graph-effect-contract.md. Sends the immutable local approved draft as a single sendMail request; operation property supports conservative Sent Items lookup. Default-off switch, tenant/hash/recipient guards and no POST retries. Request acceptance ID is distinct from message ID; accepted/sent never claims delivered/read. Shared ExecutionService restart test confirms a lost-response send is observed without a second POST.

Validation: pytest → 183 passed, including 20 Graph adapter/core cases; git diff --check passes. Existing Starlette deprecation warning remains. All new network behavior used HTTP boundary doubles; no Graph/Odoo/model call or email occurred. Composed extended-property persistence/filter behavior needs live Phase 7 verification.

Next: immutable connector-binding persistence and local review/preparation flow; scheduler queue/API and the two n8n exports/reference runner. Consent/test mailbox, OAuth refresh, payload repository wiring and connected acceptance remain pending. Automation stays active; independent implementation remains available. No full phase gate changed.

## Latest batch — durable connector binding and review API

Artifacts: backend/bindings.py, connector_bindings SQLite table/static PostgreSQL migration 005, GET/POST scoped connector-binding routes, typed input and tests/test_bindings.py. Immutable hash/preview association, unique connector proposal across local proposals, proposer-only attachment, read-only remote validation and final freshness recheck. Historical payload loader remains available for reconciliation after expiry; it does not authorize execution.

Validation: pytest → 190 passed; native MCP suites → 2 passed; migration plan regression includes 005. Evidence: docs/evidence/connector-bindings.md. All connector traffic in tests used doubles. Normal app factory has no connector configured. No external writes, spending or Docker.

Next: scheduler queue/API and two n8n exports/reference runner to exercise the shared skills and approval polling. Connector preparation and binding review UI still require implementation; PostgreSQL repository wiring and access/evaluation gates remain. No full phase gate closed.

## Latest batch — durable workflow coordination and n8n definitions

Artifacts: backend/workflows.py and queue table/migration 006, scoped enqueue/status/tick API, scripts/export_workflows.py, automation/n8n/intake-v1.json + due-v1.json, reference traversal and tests. Native checks: pytest → 201 passed; MCP → 2 suites passed; export generator and diff check pass. Evidence: docs/evidence/workflow-contracts.md.

The queue accepts reviewed commitment candidates and shares preparation, approval, eligibility, execution and reconciliation core. Leases/checkpoints recover after a dispatch-to-job-update crash without duplicate effects. Exports are inactive, use placeholder credentials/host, and make at most two ticks per schedule execution. No n8n runtime, connected effect or model spend was used.

Next: close intake/model-candidate review/enqueue and due discovery handoffs; add recovery/resubmission UI and connector binding review/preparation. Then complete PostgreSQL runtime wiring/config hardening, evaluation rubric/heldout artifacts and access-dependent gates. No Phase 5 pass is claimed from reference-runner results. Automation remains active.

## Latest batch — due discovery and recovery workspace

Artifacts: bounded latest-commitment discovery/cursor, due-before-preparation guard, recovery/list API, migration 007, WorkflowQueue React panel, domain/API and browser coverage. Validation: pytest → 207 passed; web build → passed; Edge → 3 passed. Recovery browser scenario mocks presentation data; Python cases cover actual API/domain authorization/state. Evidence: docs/evidence/due-recovery.md.

Recovery preserves operation IDs and permits observation only for existing effects; expired-proposal renewal requires new approval. Due discovery skips future/cancelled/opted-out/deleted/out-of-scope records and uses idempotent enqueue. No live adapter calls, model spend or engine/container run.

Next: intake extraction → candidate review/record → queue handoff and connector binding/preparation UI; close PostgreSQL persistence/config issues and prepare Phase 6 rubric/evaluation artifacts. Source mapping and restore review, live credentials and provider/local evaluation budgets remain outstanding. Automation active; no complete phase gate claimed.


## Latest batch — operator intake review (2026-10-10)

Added a conversation intake panel using the shared extraction, commitment recording and preparation APIs. Operator explicitly checks candidate evidence/owner/date; ambiguous extraction and cancelled candidates cannot prepare through this panel. Server-side evidence/revision checks remain authoritative. No model automatically runs; configuration is unchanged.

Validation: web TypeScript/Vite build passed; five Edge tests passed. New extraction responses are doubles, while candidate recording and proposal preparation use the actual isolated backend. Browser fixtures now isolate intake into a separate tenant after a shared-state regression was detected and fixed. No model spend, connected write or Docker operation occurred.

Remaining Phase 5: explicit intake scheduler handoff and connector preparation/binding review UI; full engine acceptance remains Phase 7. This panel prepares a proposal in the review queue, not a workflow job. A candidate can remain recorded if subsequent preparation fails; replay uses existing core idempotency. Automation remains PAUSED at user request; work continued only in this interactive session. No phase gate closed.


## Goal checkpoint — explicit intake handoff (2026-10-10)

Implemented proposer-only handoff of commitment-based proposals to the unique configured scoped worker, preserving proposal ID, approvals and independent CRM/email job identities. The API fails closed when worker configuration is missing/ambiguous. Local transaction checks freshness/owner/scope and records an audit event. UI exposes separate queue actions without executing or approving.

Validation: seven new handoff tests passed; TypeScript/Vite build passed. Full regression and browser handoff coverage remain to run before Phase 5 gate closure. Remaining goal work: Odoo preparation/binding UI, workflow/export verification and requirement-by-requirement completion audit. Automation stays PAUSED; goal active. No external calls or connected effects.


## Goal checkpoint — connector binding workspace (2026-10-10)

Added operator binding form and scoped saved-binding display, including exact remote activity preview, identity/proposal/approval references, immutable result and explicit connector-not-configured failures. Preparation instructions refer to the existing #2 workspace; no remote creation or approval is performed by this UI. Native app still has no connector configured.

Validation: full Python suite 214 passed (existing Starlette deprecation warning); TypeScript/Vite build passed; six Edge scenarios passed. Intake browser test now records/prepares/hands off against the actual local backend; only model extraction is mocked. Binding browser test checks submitted fields and disabled-connector error; adapter validation/read-only persistence is covered by Python boundary doubles. Separate browser tenants avoid fixture interference.

Both generated n8n exports now allow 240 seconds for two 65-second HTTP requests and a 60-second wait. Generator parity and reference traversal passed within the full suite. Updated workflow setup documentation covers explicit operator handoff and unique worker configuration.

Goal remains active pending final audit: preparation UX must provide a concrete field mapping/diff (current binding form requires copying the approved connector preview); strengthen positive binding browser coverage and configuration failure tests; verify Phase 5 requirements against current artifacts. PostgreSQL runtime/connected n8n/Odoo acceptance remains unproven, not inferred from local tests. Automation PAUSED. No connected writes, model spend, email or Docker.
