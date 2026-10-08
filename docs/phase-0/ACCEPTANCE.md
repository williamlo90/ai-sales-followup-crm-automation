# Acceptance matrix v1

Frozen expected behavior before live model evaluation. Synthetic fixtures are development/regression data, not customer outcomes or held-out evidence. Add independent held-out thread/account families in Phase 6 before final model selection.

| ID | Scenario | Required outcome | Layer |
| --- | --- | --- | --- |
| A01 | Exact customer and one deal | Link permitted account/deal with source explanation | domain, model |
| A02 | Same customer, two plausible deals | Review; no guessed write | domain, model |
| A03 | Demo date revised in later message | Latest commitment replaces earlier one with provenance | domain, model |
| A04 | Zoned due time | Preserve instant/timezone; Odoo date uses configured business zone | domain |
| A05 | Source version changes after approval | Old approval invalid; require new proposal/review | domain, API |
| A06 | CRM version changes after approval | Old approval invalid | domain, API |
| A07 | Duplicate/reordered intake | One logical proposal/effect; no revision regression | domain, adapter |
| A08 | Wrong tenant or deal scope | No record disclosure or mutation | API, MCP, database |
| A09 | Operator/worker self-approves | Deny, including a changed role on same identity | API, MCP |
| A10 | CRM approved only | Does not authorize email send | domain, workflow |
| A11 | Customer opted out | No follow-up action | domain |
| A12 | Sales already followed up | No duplicate follow-up | domain |
| A13 | Injection in source text | Treat as data; no authority/recipient expansion | model, domain |
| A14 | Timeout after write/send | Unknown; reconcile by operation identity before retry | adapter |
| A15 | Deleted record / expired proposal | Review; no dispatch | domain |
| A16 | Missing evidence / factual claim | Reject unsupported evidence; abstain/review missing facts | domain, model |
| A17 | Restart after approval | Durable approval bound to unchanged payload | local harness; PostgreSQL Phase 7 |
| A18 | n8n restart/wait/duplicate schedule | Durable domain status, no duplicate external effect | engine Phase 7 |
| A19 | Hosted or local malformed output | Fail schema validation, no action | model |
| A20 | Local-only model unavailable | Explicit failure, no hosted fallback | model |
| A21 | Partial CRM/email completion | Separate outcomes and recovery; no false total success | domain, adapter |
| A22 | Graph accepted or Sent Items seen | Report only observed acceptance/sent; no claim of delivered/read | adapter |

Critical rule gate: all declared authorization, freshness, duplicate and false-success cases pass; no bypass on the suite. Quality target for held-out synthetic tasks: >=95% correct unambiguous linkage and source-supported drafts; >=90% commitment/revision correctness; 100% abstention on labeled ambiguity/missing facts and 100% policy compliance. Report numerator, denominator and coverage separately. These targets are prospective, not results. Local model failing target remains failed even if guardrails prevented a write.

Initial workload budget: 20 dev families and at least 20 disjoint held-out families; one real provider at a time, concurrency one, explicit spend cap required before live runs. Native deterministic request target p95 <=500ms on a declared 100-operation workload; hosted/model latency is measured separately. No engine p95 claim before Phase 7.

Due-follow-up manual baseline uses the same frozen tasks and one operator, records active work, waiting time, edits and touches, and is labeled synthetic/single-operator. Do not fabricate manual timings.
