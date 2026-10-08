# prepare_crm_update — 1.0

Owner: Sales Operations. Binding: `SkillService.prepare_crm_update`; input: input.schema.json. Output result is the domain proposal with payload hash, version, source snapshot, evidence, approvals and validation status.

Use after candidate review/recording to prepare one activity and follow-up draft tied to the current commitment revision. Do not use for arbitrary CRM field writes; connector #2 currently supports activity creation. Requires operator/worker and scoped current deal/commitment.

Load the selected commitment, derive due date and evidence, prepare through SalesService, validate source/CRM/commitment freshness and return an immutable preview. Identical requests reuse the current proposal; expired proposals obtain a new version without approvals. Cancelled/stale commitments fail. CRM and email approval remain separate, human-controlled and bound to the payload.

Example: `{"deal_id":"deal-1","deal_version":1,"commitment":{"id":"demo","revision":1}}`. Side effect: local proposal/audit only; no remote write. Existing activity revisions need review until a supported connector update capability is added. Common exceptions and recovery: ../README.md.
