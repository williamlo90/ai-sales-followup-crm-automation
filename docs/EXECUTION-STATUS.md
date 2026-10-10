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


## Goal checkpoint — mapped Odoo preparation (2026-10-10)

Added read-only connector preparation endpoint and before/proposed-value table for new activities. Expected activity fields now share one adapter function with dispatch/binding validation; source_version comes from scoped opportunity GET. Repository rechecks local freshness after connector latency. UI can prefill binding preview from this result. Remote proposal creation/approval stays in the existing #2 workspace; no connected mutation is invoked.

Validation: 218 Python tests passed; TypeScript/Vite build passed; six Edge tests passed. New cases cover read-only mapping, context changes during remote read and missing/ambiguous worker configuration. Browser binding scenario verifies failed attachment then successful immutable display using boundary mocks; actual validation remains in Python tests. Full integration is not claimed. Existing Starlette deprecation warning remains.

Next: finish requirement-by-requirement Phase 5 audit, including workflow handoff ownership across renewal, connector-ready configuration boundaries, static PostgreSQL/engine deployment dependencies and reference-runner coverage. No phase gate closed yet. Goal active, automation PAUSED; no Docker/model spend/email/connected write.


## Phase 5 native gate completed (2026-10-10)

Requirement audit: docs/evidence/phase-5-acceptance.md. Intake handoff, Odoo read-only preparation/binding UI, both generated exports, reference endpoint traversal, evidence/diff/approvals/unknown recovery are implemented and contract-validated. Final checks: 220 Python tests, six Edge scenarios, TypeScript/Vite build and diff check passed. Renewed worker-owned proposals can use binding controls without weakening proposer-only authorization. Both due success/replay and workflow timeout budget now have explicit reference tests.

Phase 5 checklist reflects its native gate only. PostgreSQL runtime wiring remains an earlier-phase prerequisite; connected Odoo/Graph/n8n and container acceptance remain unvalidated Phase 7 work. Normal factory has no connector/execution adapter. No Phase 6/7 work was entered, no external effect occurred. Automation remains PAUSED. Next work outside this goal: resolve earlier-phase runtime/access gaps, then Phase 6 evaluation.


## Phase 6 started - gap audit and evaluation protocol (2026-10-10)

Artifacts: docs/phase-6/GAP-AUDIT.md, EVALUATION-PROTOCOL.md, dataset-preflight.json, scripts/evaluation_dataset.py and four passing tests. Preflight verifies minimum family counts, IDs, expected outcomes, source/family cross-split overlap and deterministic dataset hash; it never claims quality or semantic independence. Actual current dataset fails readiness: eight dev families and zero held-out. No dataset freeze claimed.

Read-only config check: project OpenAI key present, model ID absent, app model disabled, old canary reservation present. No key value printed. Ollama/PostgreSQL not on PATH; installation status not inferred. PostgreSQL runtime/schema mismatch and missing composition are documented with concrete next actions. User allowed discretion USD1 vs USD5; selected USD1 total additional OpenAI Phase 6 ceiling. No spend yet; persistent budget enforcement and official price verification required before paid calls.

Next: author/review the complete 20+20 family dataset, implement scoring and persistent bounded runner, then run a development pilot within the cap. PostgreSQL repository wiring remains earlier-phase work; no native/connected quality gate has been closed. Automation remains PAUSED and no new goal/automation was created.


## Phase 6 goal checkpoint - persistent budget and development draft

Added backend/evaluation_budget.py: immutable integer-microdollar cap, transactional reservations, one pending call globally, no call-ID replay, immutable settlement and retained full reservation on unknown/low usage. Observed overruns stop further calls. Restart/concurrency/unknown/replay tests pass. This component is not yet wired into a paid runner; no real budget ledger or model request was created.

Authored fixtures/evaluation/development-v2.json with 20 synthetic development families covering diverse tasks, caveats, incomplete commitments, timezone rollover and injection. Labels are explicitly draft, not frozen; revision/cancellation/multi-message coverage and full field-level expected outputs still need expansion/review. Original eight regression families remain unchanged. No held-out cases promoted from development.

Validation: 12 focused budget/dataset tests passed; existing Starlette warning only. Budget stays USD1 additional Phase 6; no spend. Next: complete family coverage and labels, author 20 separate held-out families, implement scoring/runner, verify current prices before the development pilot. Claude/Grok/native access and observed manual session remain user-dependent; question queued while independent work continues. Goal active, heartbeat PAUSED.


## Phase 6 checkpoint - local inventory and held-out candidates

User confirms OpenAI is the only hosted access available. Windows PATH, common directories, uninstall registry, processes and local ports showed no matching model runtime; bounded Ubuntu WSL shell inspection also found no common Ollama/llama executable or model manifest. No model/server/container/download started. Inventory limitations recorded in phase-6/GAP-AUDIT.md.

Authored twenty distinct held-out candidate families in fixtures/evaluation/heldout-v2.json. Combined preflight reports 20 development and 20 held-out families, no lexical/account/thread overlap and matching model/source text. Semantic label review, multi-message revision/cancellation coverage and richer expected outputs remain before freeze; no quality or generalization claim. Strengthened preflight lineage/input checks. Thirteen focused dataset/budget tests pass after correcting an edit-time indentation error.

No paid requests or new spend. Next: complete labels/coverage and scoring runner, then OpenAI development pilot under persistent USD1 ceiling. Goal remains active; unavailable providers do not block independent work. Heartbeat remains PAUSED.


## Phase 6 checkpoint - scoring and real OpenAI pilot

Added extraction scorer with exact field/revision/evidence checks and missing/error denominators. Semantic factuality remains explicitly unscored until review. Updated both 20-family draft splits with expected commitment fields, linkage and history-based reschedule/cancellation. Full semantic label/coverage review and final freeze remain pending.

Implemented scripts/evaluate_openai.py using the existing adapter and persistent USD1 ledger; explicit --run only, development case selector, no retries, exclusive output, deterministic call reservation, bounded bytes/output and conservative current-price accounting. Twenty-one focused tests passed; dry run verified no call.

One authorized actual OpenAI pilot dev-v2-01 passed automated extraction checks and agent source inspection. 547 tokens, 4552.32ms, estimated USD0.0003748 (ledger rounds to 375 microdollars); USD0.010614 reservation retained. Evidence: docs/evidence/phase-6-openai-pilot.md. Old canary untouched; no connected write or email. Claude/Grok and local-model access remain pending.

Next: complete label/semantic coverage audit, full domain/proposal/draft scoring and frozen held-out evaluation; native workload and observed manual comparison still required. Goal active, automation PAUSED. No broad quality gate or default-provider decision from N=1.


## Phase 6 checkpoint - frozen labels, real-core pipeline and native workload

Frozen version 2.0 synthetic dataset: 20 development plus 20 held-out disjoint account/thread families, exact file/scorer hashes in docs/phase-6/dataset-freeze.json. Label reviewer is explicitly the implementation agent, not an independent human annotator; shared scenario taxonomy is disclosed. Field labels, abstention, proposal counts/recipient and draft review rule are fixed before held-out use. Pilot from the earlier draft remains separate.

Added backend/evaluation_pipeline.py invoking actual SalesService/Store/match/merge/preparation with isolated local state, preserving history and rejecting unsupported evidence. Four new tests passed; 25 focused evaluation tests passed. Runner now enforces frozen file/scorer hashes and captures actual core proposals/drafts without external effects.

Measured native workload: scripts/native_workload.py, 100 calls (20 each prepare/get/context/match/due), concurrency one, temporary SQLite, Python 3.13.6 Windows. Zero errors; p50 0.498ms, p90 3.132ms, p95 3.267ms, max 5.702ms; declared 500ms p95 target met for this workload only. Evidence docs/evidence/phase-6-native-workload.json; individual samples ignored/local. No HTTP/model/PostgreSQL/n8n/platform performance inference.

Ran three additional real OpenAI development cases after freeze: reschedule dev-v2-03, cancellation dev-v2-19, ambiguity dev-v2-16. All automated extraction checks passed; actual core produced one revised proposal, no cancelled proposal, and ambiguous linkage review respectively, with zero approvals/operations. Agent inspected response and generated draft against source/history. Four total Phase 6 API calls including earlier pilot; estimated cumulative usage cost rounded USD0.001474, conservative reserved USD0.042805, reservable balance USD0.957195. No held-out API calls yet.

Next: run remaining frozen development then held-out profiles, aggregate field and semantic review results; manual comparison and Claude/Grok/local evaluation still require external inputs. Goal active, heartbeat PAUSED. No connected effects or Phase 7 execution.


## Phase 6 checkpoint - complete development baseline and diagnosed failures

Completed frozen development baseline (20 cases): 11 automated extraction passes, 9 model_output_invalid failures, all retained in denominator. Evidence docs/evidence/phase-6-development-v1.json. Held-out remains unused; gate failed, not downgraded. Paid result files remain ignored/local. Original pre-freeze pilot is separate from this denominator.

Added opt-in response capture before schema validation for evaluation only; normal app capture remains off. A diagnostic development response incorrectly requested owner/metadata already in source. Revised shared prompt to extract-v2 with explicit ID/revision initialization, source field mapping, timestamp/owner rules, history/cancellation and review consistency. Provider/runner tests: 27 passed.

Three bounded v2 development probes produced one pass and two failures: dev-v2-05 abstained despite supported named owner/date, dev-v2-10 emitted ready plus nonempty missing_information and failed the existing consistency validator. Raw diagnostic evidence now preserved, no relaxed schema or hidden repair. Further development tuning/model comparison is needed before held-out; no final quality gate claimed.

Persistent ledger: 25 calls including baseline/pilots, USD0.268028 conservative reservations, USD0.731972 reservable. Known-usage estimated total USD0.005889 is incomplete because nine earlier invalid responses lost usage; their full reservations remain charged against cap. No extra secret access, external writes, email or Docker. Goal active; heartbeat PAUSED.


## Phase 6 checkpoint - OpenAI development profile accepted for held-out

Added explicitly priced Luna low-reasoning evaluation profile, sharing the same USD1 ledger; conservative input rate includes cache-write multiplier. Three initial probes: two pass, one missed whole-thread readiness. Prompt extract-v3 clarifies incomplete activity review without changing frozen labels or scorer. Latest complete development run: 20/20 automated extraction passes, 20/20 actual-core linkage checks, expected proposal counts/recipients, zero approvals/operations. Implementation-agent source/history review passes all twenty; detailed notes and response hashes in docs/evidence/phase-6-development-luna.json. This is development evidence, not generalization or full policy acceptance.

Profile frozen before any held-out call in docs/phase-6/openai-profile-freeze.json. Luna uses an alias (no dated snapshot listed); response model retained. Full suite passed 248 tests before final prompt clarification; 30 affected provider/runner tests passed afterward. All 48 paid Phase6 calls retained: conservative committed USD0.451308, reservable USD0.548692, known-usage estimate USD0.014620 incomplete due to nine earlier unknown-usage responses. No retries, budget reset, app-config change or external effects.

Next: run untouched held-out with frozen profile, score and inspect semantics, then finish manual measurement tools and Phase7 acceptance matrix. Claude/Grok absent; no common local runtime found; manual observation still pending. Goal active, heartbeat PAUSED. Dataset-freeze checklist now checked with explicit synthetic/agent-review scope; remaining gates open.


## Phase 6 checkpoint - frozen OpenAI held-out completed

Added enforced profile/prompt/schema/dataset-manifest freeze verification before held-out calls; six runner tests pass, including changed-profile rejection. Executed twenty untouched held-out synthetic families once each with Luna low/extract-v3, concurrency one, no retries. Evidence docs/evidence/phase-6-heldout-luna.json: extraction 20/20, scoped deterministic linkage 19/19 unambiguous plus 1/1 ambiguous review, abstention 8/8, proposal-set correctness 20/20, generated draft factuality 11/11 under implementation-agent source/history review. No approvals or operations. Linkage is supplied-mapping core behavior, not model entity resolution. Shared taxonomy/short synthetic sources, agent review and alias limitations remain explicit.

Model-call latency N=20 nearest-rank: p50 2386.79ms, p90 2951.87ms, p95 3092.24ms, max 4251ms; excludes domain/UI/engine. No rerun or tuning against held-out. Full native suite 249 passed (10.34s, one existing Starlette deprecation warning); raw JUnit local/phase-6/native-tests.xml. Added Phase7 acceptance handoff matrix with native evidence and actual observation requirements, not connected acceptance.

Budget ledger now 68 calls: USD0.610983 conservative committed, USD0.389017 reservable, USD0.022155 known-usage upper estimate (incomplete total because nine early invalid outputs lost usage, reservations retained). No cap increase/reset, pending call, overrun, app-model enablement, connected effect, Docker or Phase7 execution.

Next: audit native policy matrix against actual assertions and JUnit, prepare observed manual-vs-assisted capture/session and resource/candidate audit. Other hosted APIs unavailable per user; no local model runtime found in bounded inventory. Model installation/access and real manual observation remain external dependencies. Full Phase6 is not complete; goal active, heartbeat PAUSED. Previous goal turn was substantive progress, not a blocked/no-progress turn.


## Phase 6 checkpoint - policy mapping and human session prepared

Mapped acceptance A01-A22 to observed passing native assertions in docs/evidence/phase-6-policy-coverage.json, tied to the 249-test JUnit hash. A18 remains actual engine pending; PostgreSQL/MCP/real local inference/connected effects are explicitly not inferred from API/SQLite/transport doubles. This mapping is not a claim that all connected layers passed.

User agreed to a real manual session. Prepared frozen four paired/eight task due-review worksheet, alternating manual/assisted order, using actual due_eligibility core for cached assistance. Artifact local/phase-6/manual-review.html; instructions docs/phase-6/MANUAL-SESSION.md. Browser records active/paused intervals, field changes, submissions, source hash and answers; export JSON awaits human execution. Assistance is deterministic/cached, so system waiting is unmeasured/null, not fabricated AI latency. Single-operator synthetic worksheet scope remains distinct from full CRM workflow/ROI. Optional CLI interval recorder has two passing tests.

Native Edge headless QA passed eight-task traversal, required fields, pause hiding and JSON download. Automated QA output was not saved as human evidence. Screenshot visually inspected; no overflow at 1100x900. Resource inventory: 16 logical processors, 16,868,962,304 bytes physical RAM, approx 3.73 GiB free at observation; RTX4050 Laptop GPU plus Intel UHD identified (WMI VRAM not trusted as true VRAM capacity), C: 464,784,535,552 bytes free. This is an idle snapshot, not peak workload resource evidence or local-model acceptance.

No new API spend. Next: receive/validate human session, complete native resource/candidate audit and address remaining local/Claude/Grok access. Independent preparatory work progressed this turn; no blocked threshold. Goal active, heartbeat PAUSED, no Phase7 execution.


## Phase 6 checkpoint - observed-session validation and native resources

Added scripts/score_manual_review.py: validates fixture hash, complete task order/mode, initial answers, event state/replay, aware timestamps, active/paused durations and edit counts; rejects cached assistance with fabricated system waiting. Outputs per-task correctness and mode totals with explicit no-human-authenticity/no-ROI caveats. Eight new scorer tests plus two CLI timer tests pass. No human session received or synthesized.

Added Windows native resource measurement around the actual 100-operation core workload. Declared before run: concurrency1, peak working set256MiB, CPU5s, wall10s. Observed peak37,793,792 bytes, CPU0.1875s, wall0.467s, zero errors, p95 3.368ms. Evidence docs/evidence/phase-6-native-resources.json; raw samples ignored/local. Process lifetime peak includes imports/setup; no model/GPU/full-stack inference. The previous latency run is preserved separately.

Requirement audit docs/phase-6/COMPLETION-AUDIT.md keeps full goal incomplete: human export, other-provider/local evidence and full candidate freeze remain; earlier PostgreSQL/connector composition gap remains explicit for connected release. No new API spend/external effect, no heartbeat resumption. Previous turn and this turn made concrete progress; blocked threshold not reached. Next: validate user export when supplied; finish model-access preparation without assuming credentials, installing unchosen runtimes or changing approved spend.


## Phase 6 checkpoint - authorized local model preparation and live download

User explicitly approved standalone Ollama + Qwen3 download (~2.9GB, 8GB disk allocation) and bounded native evaluation, outside OneDrive, no service/startup. Official v0.40.2 release asset is 1,468,085,195 bytes; expected SHA256 pinned in LOCAL-MODEL-PROPOSAL.md. NVIDIA-SMI confirms RTX4050 Laptop GPU 6141MiB total/5601MiB free VRAM (corrects unreliable WMI byte report without changing raw history).

Runtime archive download started in unified exec session 98246. Last authoritative poll: process still running; archive grew to 504,117,947 bytes. Command downloads once, verifies checksum and then extracts to C:/Users/William/.cache/sales-phase6/ollama-v0.40.2. Do not restart/download again because observation yields. Poll session 98246; inspect terminal state and archive hash before recovery if handle disappears. No runtime server or model inference started. Current free host RAM ~3.61GiB remains below proposed 4GiB pre-launch threshold; don't stop other apps or silently lower resource gate.

Added explicit Ollama think=false profile option and pinned-development runner scripts/evaluate_local.py. Checks runtime version/full model digest/non-thinking support and frozen dataset/scorer before one call; exclusive result and one-active marker; transport/unknown failures retain marker until owned-server observation/stop, no automatic retry. No hosted fallback. Twenty-seven provider/local-metadata tests pass; OpenAI runner/provider combined32 tests passed before local marker refinement. No inference or quality claim from these doubles. Commit124060e.

Next: finish and verify the live runtime download, recheck resource headroom, obtain pinned model using isolated own server only when preconditions hold; run one dev pilot before expanding. User manual export still pending, Claude/Grok access absent. Goal remains active; this turn includes substantive implementation and a verified live download wait, not a blocked/no-progress turn. Heartbeat stays PAUSED.


## Local runtime download continuation

Revalidated session98246 repeatedly as live; last measured archive1,069,829,696 bytes of1,468,085,195, no terminal/error output. No retry/new downloader. User agreed to free RAM; most recent sampled free host RAM3,331,300KiB still below4GiB, so no inference/server launch yet. Do not infer the user's agreement means memory is already available.

Added scripts/start-local-evaluation.ps1 with native pre-launch host/GPU headroom checks, occupied-port/owner-record refusal, loopback-only no-cloud environment, one-model/one-request limits, hidden own process and PID/start-time/executable record. PowerShell parser check passed; script not executed. Runtime extraction/checksum remain in existing live download command. Next continuation must poll session98246, inspect final checksum/extraction result and resource headroom; never treat this observation yield as process failure. Goal turn is verified wait plus launch implementation progress. Other work/user manual export and Claude/Grok remain unchanged.


## Phase 6 checkpoint - real local model evaluated and stopped

Download session98246 completed: official Ollama0.40.2 archive checksum matched and extraction succeeded. User freed RAM; pre-launch available4,897,320KiB host /5501MiB VRAM passed thresholds. Started only project-owned loopback server PID35556, verified version/listener ownership and explicit cloud-disabled log. Model pull session59004 completed successfully: qwen3:1.7b Q4_K_M,1,359,293,444 bytes, full digest8f68893c685c3ddff2aa3fffce2aa60a30bb2da65ca488b61fff134a4d1730e7. /api/show explicitly supports false thinking.

Ran all20 frozen development cases once through shared adapter/core with think=false,4096context/output,temperature0,keep_alive0. Pilot session16554 and remaining batch2695 are terminal success as runner processes; model quality failed0/20:16 invalid responses,4 valid-schema but unsupported commitments. Evidence docs/evidence/phase-6-local-qwen3.json retains per-case raw hashes and denominators. No held-out local calls or prompt tuning; guardrail review does not convert failures into success. Local evaluation activity is complete with rejected profile, not local-model quality acceptance. OpenAI profile remains the accepted quality candidate.

Ollama-reported total durations N20: p50 3895.65ms,p90 4168.06ms,p95 4187.76ms,max53318.29ms (first initialization includes24.26s load). This differs from client/engine latency. Resource sample during pilot stayed above host/VRAM headroom; server-only peak170,504,192bytes excludes child runner peak. Before each subsequent case host>=4GiB and VRAM>=3GiB checked. No timeout/pending marker. /api/ps empty after run; verified PID/path/start-time ownership, stopped35556, no listener/child processes remained. Historical owner and stop records retained in .cache/sales-phase6. No service/startup entry. Total cache disk4,769,935,492bytes, within approved8GB allocation.

Full native suite261 passed in10.97s, existing Starlette warning only. Updated local evaluation checklist and completion audit truthfully. API spend unchanged. Remaining Phase6: actual human manual export/scoring, Claude/Grok project access and bounded real comparison, final candidate audit/freeze. Earlier PostgreSQL/connector composition is still required before connected release; no Phase7 entered. Goal active, heartbeat PAUSED. This turn made substantive progress (downloads,20 real calls,resource observations and shutdown), not blocked/no-progress.


## Phase 6 checkpoint - actual human session received and scored

User said manual session done. Located exact sales-manual-session-8c9811c0-7df0-4a40-b22b-00286816743c.json in Downloads; preserved unchanged in ignored local/phase-6. SHA256038adb3f8fb92f5e531d2c83240764014c777de340f7e9dfe6a31a57fc751677. Existing scorer validated complete8 IDs/order/mode, frozen fixture hash, event transitions, answer replay, timestamps and active intervals. No synthetic timing or replaced answers. Evidence docs/evidence/phase-6-manual-comparison.json.

Observed manual3/4 correct,205.298s active,8 field entries and4 submissions; assisted4/4 correct,125.2705s active,0 field edits and4 submissions. Assisted faster in2/4 pairs, not uniformly. First manual task141.82s accounts for much of aggregate difference; no causal speedup/customer ROI claimed. Manual-p3-1 selected eligible=true/not_due but labeled already_contacted=false eligibility. No assisted correction; post-submission rework time not observed. No pauses recorded. Active time includes reading/page overhead, not continuous attention proof.

This closes receipt and scoring of the requested worksheet session, not full live workflow/waiting comparison. Cached deterministic suggestions involved no measured system wait; keep null, don't add unrelated hosted latency or invent remediation time. Phase6 manual row remains scoped/partial while full requirement audit retains that gap. Other-model access comparison and final candidate freeze remain outstanding. No new model calls, installations or external effects. Goal active, heartbeat PAUSED; substantial new user evidence this turn.

## Phase 6 checkpoint - live worksheet measurement instrument

Added scripts/live_manual_review.py and score_live_manual_review.py, reusing the existing worksheet and shared due_eligibility core. Loopback-only host/origin/key checks, one request per session/case, exclusive authoritative receipts; browser request waiting is separate from active work, including hidden-tab auto-pause after an asynchronous response. Scorer verifies receipt hash/content, timestamps, no overlap, answer replay and edit counts without mutating source observations. First human session remains unchanged; no second human result claimed.

Validation: `.venv/Scripts/python.exe -m pytest -q` ->268 passed in9.85s, existing Starlette deprecation warning. Seven new tests cover access/replay and valid/tampered measurements. Native Edge headless completed8 tasks using actual local requests, pause/resume and downloaded export; scorer validated that export against separate automated-QA receipts. Ignored QA artifacts are under local/phase-6/live-manual-automated-qa and are not human evidence. Owned QA server session80606 stopped; port8046 has no listener. No model calls or spending.

Next: a separately observed follow-up session can measure local core request waiting using instructions in MANUAL-SESSION.md; this does not establish full CRM/model workflow benefit. Claude/Grok project access/budget and final candidate audit remain outstanding. Goal active, heartbeat paused; instrument implementation and validation are substantive progress, not a blocked-only turn. Unrelated portfolio README/PROJECT-DELIVERY/CASE-STUDY edits preserved.

## Phase 6 checkpoint - accepted responses replayed against current core

Previous turn classified as progress (live worksheet implementation and validation). Added scripts/replay_phase6.py: verifies frozen dataset/scorer/profile, exact published response hashes and IDs, recomputes scoring and replays actual core in isolated temporary SQLite stores. Compares complete pipeline records including payload/draft/recipient/evidence/approval/operation data, excluding only random proposal UUIDs. All40 accepted development/held-out responses unchanged. Command: `.venv/Scripts/python.exe -m scripts.replay_phase6 --output local/phase-6/offline-replay-current.json`; report preserved in docs/evidence/phase-6-offline-replay.json. No paid calls, network, connected effects or ledger edits.

Six new replay tests passed in0.55s via `.venv/Scripts/python.exe -m pytest tests/test_phase6_replay.py -q`; cover material tampering and UUID-only equivalence. Prior full suite268 passed; no claim of a new full-suite run. Updated stale protocol/handoff status to reflect completed OpenAI/local/first-human work. Candidate freeze still pending Claude/Grok access/budget and observed live waiting. No owned runtime left running. Goal active and heartbeat paused. This turn produced new reproducibility evidence and a reusable offline verifier; not a blocked-only turn.


## User-approved V1 scope decision - 2026-10-10

User approved OpenAI as the sole V1 hosted provider; Claude/Grok evaluation is optional, not a remaining V1 blocker. Existing adapters are implemented, not live API-validated. Updated Phase6 checklist, protocol, completion audit and Phase7 handoff; historical evidence is unchanged. Remaining Phase6 work: observed waiting-time session using prepared live worksheet, then final audit/candidate freeze. No new model calls, fees or Phase7 execution. Heartbeat remains paused.


## Phase6 completion - approved OpenAI-only V1, 2026-10-10

User supplied actual live worksheet export6d581f29-a3b9-4a66-978e-490e71c13f16. Preserved raw SHA25620250ed3e0770aba581791d05193b0bf937a8973db6cdac20f2be47ae0fa865b. score_live_manual_review validated frozen fixture/order/time/answers and four authoritative receipts. Manual3/4 correct,96.1336s active,8 initial field entries; assisted4/4,64.2043s active,0 edits,0.0343s total HTTP/core wait. Four submissions each. Manual already-contacted case answered eligible; no correction time invented. User-attested repeated synthetic worksheet, not customer ROI or AI/CRM latency. Evidence phase-6-live-manual-comparison.json. Owned server94107 stopped after export.

Final pytest274 passed11.30s (existing Starlette warning); final offline replay40/40 unchanged. Read-only ledger:68 calls,610983microUSD committed of1000000cap,pending0; no new calls. candidate-freeze.json pins source/evidence hashes and selected scope. Completion audit closes Phase6 native gates after user-approved Claude/Grok deferral. PostgreSQL runtime and connector composition remain Phase7 prerequisites; matrix explicitly preserves connected/engine/send/load/operations acceptance. No Phase7 execution, email, cloud or container work. Heartbeat remains paused. Other portfolio edits left untouched.

## Phase7 started - transaction foundation and database probe

User authorized continuation. See docs/phase-7/EXECUTION.md for resource inventory, code changes and exact next actions. User freed RAM to5.1GiB; Docker startup reduced free RAM to1.4-1.6GiB and three sibling ERPNext containers were observed running. No sibling service changed and no project container launched. Added explicit PostgreSQL tenant transaction helper and guarded real migration/RLS probe, pinned project driver3.3.6, serialized migration checksum-table initialization. Ten targeted tests pass; real database probe remains unexecuted due headroom. Repository/app and connector composition are still outstanding; no claim that Phase7A is complete. Phase6 freeze remains historical immutable evidence, not a hash assertion about subsequent Phase7 source changes. No model charges/email/cloud. Heartbeat paused.


## Phase7 PostgreSQL256MiB actual probe passed

User approved bounded256MB database session with RAM monitoring. Cached PostgreSQL17.11 digest used in isolated container/database/volume. Six real migration/session checks passed; all7 migrations applied/replayed, RLS absent-context/read/write, rollback and checksum drift checked. Evidence docs/evidence/phase-7-postgres-256mb.json. Lowest sampled host RAM1.17GiB, post-probe container55.7MiB (not peak), no OOM. Owned container stopped; three sibling ERPNext IDs unchanged/running. No image pull/model/connected external effects. Full app PostgreSQL repository wiring remains next; Phase7A not complete.


## Phase7 application PostgreSQL slice passed within256MiB

User authorized application wiring, persistence/approval/concurrency,256MB and sibling isolation. Implemented backend/postgres_store.py plus SALES_STORAGE=postgresql factory selection; all domain/skill/workflow/ingestion/execution/binding transactions pass authenticated actors. Shared business core unchanged; explicit schema/SQL/type mapping and per-tenant transaction locks. Runtime database role checks actor active/role, RLS tenant context, no implicit SQLite fallback or migrations. Documentation docs/phase-7/POSTGRES-RUNTIME.md.

Application acceptance uses actual FastAPI factory via ASGI TestClient against real PostgreSQL17.11.12 checks passed including7 migrations/replay, RLS/rollback/checksum,8 concurrent proposals ->1 record+audit,8 concurrent approvals ->1 CRM approval+audit, role/tenant denial, new-interpreter persistence, stale-source invalidation and zero dispatched operations. Evidence docs/evidence/phase-7-postgres-app-256mb.json. Host RAM sampled minimum1.58GiB; container post-probe25.71MiB/256MiB, no OOM. Owned container stopped; three sibling ERPNext IDs unchanged. No external business write/send/model/cloud.

Full native suite286 passed11.03s, existing Starlette warning; git diff check passed. This closes the requested focused app/database slice, not full Phase7: actual server restart, remaining PostgreSQL workflow paths, connector composition and n8n/Odoo/Graph/load/recovery remain. Historical Phase6 candidate hashes are preserved. User portfolio edits untouched.


## Phase7 restart and intake/due persistence

User requested continuation. Extended postgres acceptance with actual controlled owned-container restart and intake/due workflow checks.15 real checks passed including duplicate enqueue,2 simultaneous ticks ->one claim, due cursor replay, real postmaster restart preserving approval/intake+due jobs/schedule/released lease.14 targeted native tests passed0.74s, including restart guard refusing nonmatching container ID/label/memory. Evidence docs/evidence/phase-7-postgres-workflow-restart.json.256MiB cap retained, sampled host minimum2.82GiB free, post-probe13.56MiB (not peak), no OOM. Owned container stopped and same3 sibling ERPNext IDs remain running. No email/CRM/model/other project changes. n8n engine/Graph/Odoo and abrupt-failure/load acceptance remain pending; no full Phase7 claim.


## Phase7 ingestion/execution and connector composition

User authorized continuation.19 actual PostgreSQL checks pass under256MiB, including invalid-page atomic rollback, ingestion reconnect/replay, concurrent one-operation ledger, unknown reconciliation without redispatch using explicitly simulated remote adapters. Evidence docs/evidence/phase-7-postgres-ingestion-execution.json. Host RAM minimum sampled2.58GiB, no OOM, owned container stopped, same3 sibling containers untouched.

Added connector_runtime strict project-local configuration, Odoo/Graph adapter/router composition, exact-worker Graph polling and Odoo local-tenant checks. Writes/sends unconditionally disabled; startup does not read missing tokens or contact remote services.7 composition tests passed plus prior full suite289. Example/setup ready. Real Graph/Odoo acceptance awaits authorized sandbox mappings/token paths; do not describe doubles as connected proof. No model/email/cloud or sibling data changes.
