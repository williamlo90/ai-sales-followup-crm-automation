# Phase 6 completion audit

Status: incomplete. Native/OpenAI evidence is available; the full goal is not achieved. Heartbeat remains paused.

| Requirement | Authoritative evidence | Status / remaining work |
| --- | --- | --- |
| Frozen disjoint 20+20 families and source-backed labels | dataset-freeze.json; development-v2/heldout-v2; dataset preflight | Complete for authored synthetic, implementation-agent-reviewed scope; shared taxonomy limitation explicit. |
| Scoring, source fields, revision and denominator rules | evaluation_scoring.py hash in freeze; scoring tests; profile freeze checks | Implemented and tested. Prose reviewed separately, not inferred from schema. |
| Persistent additional OpenAI USD1 cap | evaluation_budget.py and local ledger; price document | Enforced; 68 calls, USD0.610983 conservative commitment; unknown usage reservations retained. No more paid calls needed for accepted profile now. |
| OpenAI development and held-out | phase-6-development-luna.json / phase-6-heldout-luna.json | 20/20 each; held-out 19/19 scoped unambiguous linkage, 8/8 abstention, 11/11 generated draft factuality. Not independent human or customer evidence. |
| Critical policy coverage | phase-6-policy-coverage.json tied to native JUnit | Native assertions mapped; real engine A18 and connected/DB-layer acceptance explicitly deferred. No claim of full connected policy validation. |
| Claude and Grok comparison | GAP-AUDIT.md; user says only OpenAI available | Pending project-scoped API access, current model/prices and authorized spend, then real same-task evaluation. No sibling credentials. |
| Local profile evaluation | Bounded Windows/WSL inventory | Pending discovered or installed runtime/model and resource-qualified execution. Guardrails alone cannot pass model quality. |
| Manual vs assisted | manual-review-v1.json; manual-review.html; MANUAL-SESSION.md; score_manual_review.py | User agreed; waiting for actual completed human export. Worksheet measures cached deterministic due-review assistance, not full CRM/AI waiting time. Full workflow/waiting benefit remains unmeasured. |
| Native workload / resources | phase-6-native-workload.json; phase-6-native-resources.json | 100-operation core scope measured. New resource run: 0 errors, p95 3.368ms, lifetime peak RSS 37,793,792 bytes, CPU 0.1875s, wall including setup 0.467s. Within declared per-run budget. Not stack capacity. |
| Candidate freeze and Phase7 matrix | openai-profile-freeze.json; PHASE-7-ACCEPTANCE-MATRIX.md | Model evaluation profile frozen. Full release-candidate freeze pending remaining Phase6 evidence; matrix prepared, no Phase7 execution. |
| Earlier runtime prerequisites | GAP-AUDIT.md | PostgreSQL repository/transaction and connector composition still need implementation/real acceptance before connected release; native fixtures do not close these gaps. |

Human-session scorer validates exact fixture hash, task order/mode, initial answers, event transitions, timestamps, interval/count consistency and answer replay. It reports correctness and raw work/edit totals; data consistency cannot prove human authorship. It does not replace missing session data or report ROI.

Stop conditions remain: no Docker/build/pull/container, connected mutation, email, cloud or Phase7 in this goal. Other-model access and actual operator observation are external inputs. Preserve remaining scope; do not reinterpret this audit as completion approval.
