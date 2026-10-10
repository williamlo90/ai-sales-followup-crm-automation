# Phase 6 completion audit

Status: Phase6 complete for user-approved OpenAI-only V1 native evaluation,2026-10-10. Candidate is frozen for Phase7 handoff, not a connected/release candidate. Heartbeat remains paused.

| Requirement | Authoritative evidence | Status / remaining work |
| --- | --- | --- |
| Frozen disjoint 20+20 families and source-backed labels | dataset-freeze.json; development-v2/heldout-v2; dataset preflight | Complete for authored synthetic, implementation-agent-reviewed scope; shared taxonomy limitation explicit. |
| Scoring, source fields, revision and denominator rules | evaluation_scoring.py hash in freeze; scoring tests; profile freeze checks | Implemented and tested. Prose reviewed separately, not inferred from schema. |
| Persistent additional OpenAI USD1 cap | evaluation_budget.py and local ledger; price document | Enforced; 68 calls, USD0.610983 conservative commitment; unknown usage reservations retained. No more paid calls needed for accepted profile now. |
| OpenAI development and held-out | phase-6-development-luna.json / phase-6-heldout-luna.json | 20/20 each; held-out 19/19 scoped unambiguous linkage, 8/8 abstention, 11/11 generated draft factuality. Not independent human or customer evidence. |
| Critical policy coverage | phase-6-policy-coverage.json tied to native JUnit | Native assertions mapped; real engine A18 and connected/DB-layer acceptance explicitly deferred. No claim of full connected policy validation. |
| Hosted provider scope | User decision2026-10-10; OpenAI development/held-out evidence | OpenAI-only V1. Claude/Grok comparison is optional and no longer blocks V1. Their adapters remain implemented, not live API-validated. |
| Local profile evaluation | phase-6-local-qwen3.json; pinned standalone runtime and model digest | Actual20-case development evaluation completed:0/20, profile rejected. Four valid-schema responses still invented commitments. No held-out claim; guardrail abstention not model correctness. |
| Manual vs assisted | phase-6-manual-comparison.json; phase-6-live-manual-comparison.json; server receipts | Two user-attested sessions, each4 paired tasks. Follow-up: manual3/4 correct,96.1336s active; assisted4/4,64.2043s active plus0.0343s total local-request wait. No populated-field revisions. Single-operator repeated synthetic worksheet; not full CRM/AI latency or ROI. |
| Native workload / resources | phase-6-native-workload.json; phase-6-native-resources.json | 100-operation core scope measured. New resource run: 0 errors, p95 3.368ms, lifetime peak RSS 37,793,792 bytes, CPU 0.1875s, wall including setup 0.467s. Within declared per-run budget. Not stack capacity. |
| Candidate freeze and Phase7 matrix | openai-profile-freeze.json; PHASE-7-ACCEPTANCE-MATRIX.md | Native evaluation candidate frozen in candidate-freeze.json, source/evidence hashes pinned;274 native tests pass,40 response replays unchanged. Matrix prepared; no Phase7 execution. |
| Earlier runtime prerequisites | GAP-AUDIT.md | PostgreSQL repository/transaction and connector composition still need implementation/real acceptance before connected release; native fixtures do not close these gaps. |

Human-session scorer validates exact fixture hash, task order/mode, initial answers, event transitions, timestamps, interval/count consistency and answer replay. It reports correctness and raw work/edit totals; data consistency cannot prove human authorship. It does not replace missing session data or report ROI.

Current-core replay: scripts/replay_phase6.py reproduced the frozen scorer result and complete core pipeline for all40 accepted OpenAI development/held-out responses, ignoring only newly generated proposal UUIDs. Evidence: docs/evidence/phase-6-offline-replay.json. Each response matches its published semantic-review hash; each local record has a retained raw hash. Six tests reject response, payload, score, count and dataset drift. This is offline regression evidence, not new model evaluation or independent semantic review.

Follow-up human export6d581f29-a3b9-4a66-978e-490e71c13f16 validated against four server receipts, frozen fixture, event replay and timestamps. Raw export retained unchanged locally. Manual error was already-contacted eligibility. Post-submission remediation is outside this decision task and has no invented timing. Both sessions remain separate; repeated-task learning prevents causal speedup claims.

Stop conditions remain: no Docker/build/pull/container, connected mutation, email, cloud or Phase7 in this goal. Claude/Grok access is needed only if the optional comparison is later selected. Phase7 must first implement PostgreSQL repository/transaction and connector composition prerequisites, then validate real services. Completion here does not close those connected-release requirements.
