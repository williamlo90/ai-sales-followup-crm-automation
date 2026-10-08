# Sales rules checkpoint — 2026-10-09

58 Python tests passed (`.venv/Scripts/python.exe -m pytest -q`, 2.51s); the existing full browser scenario passed after API/schema changes. One upstream HTTPX TestClient deprecation warning remains. No live adapter/model, container or email operation ran.

New checks demonstrate scoped matching and ambiguity review; explicit commitment revision/cancellation history; conflicting/missing predecessors; source timestamp checks; zoned due-time comparison; due eligibility gates; exactly one contract-double effect under eight concurrent requests; proposal wording changes do not duplicate the same source-revision action; persisted dispatch and timeout -> unknown -> read-back reconciliation; separate CRM/email outcomes; recipient allowlist and send switch; rejection of mismatched receipt identity/hash; a new message invalidates an earlier approval; completed/unknown operations cannot become a fresh due job.

`backend/execution.py` is invoked only by local contract tests in this checkpoint. The production factory exposes no dispatch endpoint and defaults remain disabled. The adapter double is in tests/doubles.py. The UI therefore still truthfully says external actions are disabled.

Commitment records are source-linked candidates; substring/timestamp validation is not semantic verification of an extracted deadline. The next slice must bind reviewed commitment revisions to generated proposals and evaluate semantic extraction through model profiles. `fixtures/conversations-v1.json` is a frozen expected-outcome corpus for that work, not a passed model evaluation. `fixtures/rules-v1.json` drives 12 deterministic cases.

PostgreSQL 002 migration is prepared statically, with backfill/NOT NULL tightening explicitly pending if existing operations are present. Runtime PostgreSQL wiring, transaction locks and database acceptance remain unverified. Adapter preconditions must eventually be enforced atomically at the connected platform; a local preflight cannot prevent a remote concurrent edit on its own.

Effect policy currently permits one CRM activity and one email per selected source revision set/deal. Multi-commitment activity splitting and changed-revision updates must be designed before claiming arbitrary follow-up coverage. Do not mistake this deliberately narrow rule for full Phase 2 completion.
