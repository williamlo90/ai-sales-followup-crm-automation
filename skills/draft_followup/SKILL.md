# draft_followup — 1.0

Owner: Sales Operations. Binding: `SkillService.draft_followup`; input: input.schema.json. Result: proposal_id, payload_hash, recipient, draft, review_required=true and send_enabled=false.

Use to retrieve the source-quoted draft bound to a fresh reviewed proposal. Do not use as evidence of an email send or as unrestricted creative generation. Requires a readable scoped proposal. Validate freshness, return its exact draft/hash and server-derived recipient for human review. No external tools or writes.

Example: `{"proposal_id":"proposal-uuid"}`. Repeated reads are idempotent; stale proposal errors require preparing a new version, never silently revising an approved payload. This initial implementation uses a deterministic source-quoting template, not a separately validated model drafting profile. Common timeout/cancellation/verification rules: ../README.md.
