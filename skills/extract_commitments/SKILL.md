# extract_commitments — 1.0

Owner: Sales Operations. Binding: `SkillService.extract_commitments`; input: input.schema.json. Output: envelope plus extraction.schema.json, trace, run_id and review_required=true.

Use to extract candidate commitments from scoped ingested sources. Do not use to resolve unknown identity, grant approval, change CRM or send. Requires operator/worker role, deal scope, sources and a configured model profile.

Load server-owned sources/context, invoke one structured generation request, validate schema and quote/source/timestamp provenance, recheck source and CRM versions after inference, return candidates for review. Missing/ambiguous facts require review. Unsupported evidence and changed context fail. This skill never persists candidates as approved commitments.

Example input: `{"deal_id":"deal-1"}`. Tools: configured provider extraction only, scoped source/CRM reads and metadata audit writes. No action tools. Retry only through a new explicitly budgeted request after diagnosis. A model response is not proof of semantic correctness; use the labeled corpus and real-provider evaluation before making quality claims. Common timeout/cancellation/recovery rules are in ../README.md.
