# Application skills v1.0

These are executable business capabilities bound to `backend.skills.SkillService`, not installed Codex skills. HTTP `POST /v1/skills/{name}` authenticates the actor and calls the same binding used directly in contract tests. MCP/n8n callers will reuse this endpoint. No skill grants approval or sends email.

Inputs are strict Pydantic contracts with exported JSON Schema. `output.schema.json` describes the stable envelope; result objects use the domain result contracts documented by each skill. Extraction also has a full nested result schema. Regenerate with `python -m scripts.export_skill_schemas` after contract changes. Result schemas for non-extraction skills must become fully explicit before external release.

Common owner: Sales Operations. Common exceptions: missing scope -> forbidden/not found; stale source/CRM/commitment -> review; missing model -> unavailable. Generation makes one bounded request with 60-second transport timeout, no automatic retry or provider fallback. Per-profile call count is capped; real-profile configuration/spend cap is pending. Input/output size limits apply. Process cancellation may leave a model run marked started; that is not a successful result. No action compensation is needed for extraction/drafting. Unknown external actions must be reconciled, never resent by these skills.

Evidence: tests/test_skills.py, tests/test_providers.py, tests/test_commitment_proposals.py; fixtures/rules-v1.json and fixtures/conversations-v1.json. Metadata-only model_runs records capture provider/model/schema/prompt versions, status, latency and reported usage; unknown cost stays null. Claims and secrets are not stored in that trace. All current model calls are contract doubles; live quality/provider validation remains pending.

Changelog 1.0: strict input contracts, shared binding, source checks, proposal binding and stored/adapter reconciliation distinction. New required fields require a schema version bump. Interactive API reuse is tested; actual MCP/automation callers and a second business configuration remain acceptance work.
