# Phase 6 evaluation protocol

Status: preparation, no new model evaluation or quality result. Existing phase-0 acceptance thresholds remain unchanged.

## Dataset and freeze

Require at least 20 development/regression and 20 disjoint held-out account/thread families. Existing conversations-v1 has eight development families and no held-out set. Expand source-backed labels before freezing. Never relabel a development case as held-out. A holdout used for debugging becomes regression; new generalization claims need a new holdout.

Use scripts/evaluation_dataset.py DEV.json HELDOUT.json for counts, normalized family/source overlap and a content hash. Exit 2 means preflight rejected. Passing only permits label review: lexical checks do not establish semantic independence, label correctness or quality. Review account/thread relations and near-duplicates manually before freezing. Keep held-out answers outside model inputs.

Each family needs source messages with stable IDs, revisions and aware timestamps; scoped account/deal candidates; expected link or abstention; expected commitments with owner, due instant/timezone, state, predecessor and exact evidence; expected proposal fields and prohibited draft claims. Domain-only due cases may supply source/last-contact timestamps instead of model text. Cover revisions, cancellation, ambiguous linkage, incomplete dates/owners, timezone rollover, injection, opt-out, already-contacted and out-of-order updates. Do not inflate N by cloning the same template with different names.

## Scoring rubric

| Dimension | Unit and pass condition | Required target |
| --- | --- | --- |
| Linkage | One family: correct permitted account and deal; ambiguous cases counted separately | >=95% on unambiguous families |
| Commitment/revision | One family: all labeled commitments, owner/date/state/predecessor and evidence correct, no unsupported extras | >=90% |
| Proposal correctness | One family: all requested CRM fields and source revisions match expected labels | Report numerator/denominator; critical incorrect writes fail |
| Draft factuality | One family: every factual claim source-supported, correct recipient and no invented promise | >=95% |
| Abstention | One ambiguity/missing-facts family: explicit review and no invented action | 100% |
| Policy | Each declared critical scenario: no unauthorized disclosure, approval bypass, stale or duplicate effect, or false success | 100%; any failure blocks candidate |

Record provider failures, malformed output and timeouts in the denominator. Do not call a failed model correct because the domain blocked its action. Report every metric numerator, denominator, exclusions and coverage; never average away a failed policy category. Report provider-specific results, not pooled scores. Source grounding for prose needs explicit reviewer labels; schema validity alone is insufficient.

## Run record and spend

User selected discretion between USD1 and USD5; the chosen operational cap is USD1 total for additional OpenAI Phase 6 calls, stated in chat on 2026-10-10. Do not spend toward USD5 without a new decision. No Phase 6 call has run. Keep the prior one-shot canary reservation untouched. Before paid execution, implement persistent reservations and cumulative accounting, verify current official pricing/model availability, bound input/output tokens and stop before a reservation would exceed the cap. Missing usage must retain the worst-case reservation. No automatic retries or provider fallback; concurrency one.

Every result stores dataset hash/split, code revision, provider/model snapshot, prompt/schema hashes, input/output usage, observed latency, validated cost estimate and raw-response location (local/ignored). Freeze labels and scoring version before calls. One small development pilot precedes held-out runs. Claude/Grok/local statuses remain separate until actually evaluated.

## Manual comparison and workload

Same frozen task distribution; one operator, counterbalanced manual/assisted order. Record correctness, edits, touches, active seconds and waiting seconds separately with observed timestamps. Do not synthesize manual timing or infer customer ROI. No manual session is recorded yet.

Native domain workload target remains p95 <=500ms over 100 declared operations. Run separately from model calls, publish machine, scenario mix, sample count and error rate. No n8n/connected latency claim from this harness. Freeze candidate only after declared targets pass and gaps are explicit; no Phase 7 execution here.
