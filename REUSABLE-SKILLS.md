# Reusable sales skills

These four application skills are implemented once in the Python business core and exposed to callers through typed contracts. Each package in `skills/<name>/` has a `SKILL.md`, schema and binding. Approval, tenant scope and idempotency stay in the shared service rather than being copied into prompts or n8n nodes.

| Skill | Result | Side-effect rule |
| --- | --- | --- |
| `extract_commitments` | Source-backed claims and conflicts | Read-only; unsupported/ambiguous claims go to review. |
| `prepare_crm_update` | Current-to-proposed CRM diff and activity | Requires exact-version independent approval before write. |
| `draft_followup` | Reviewable email draft from the approved context | Draft creation does not send. |
| `reconcile_followup` | Observed CRM or mailbox operation state | Unknown outcomes are observed before any new dispatch. |

The FastAPI app, MCP stdio reference client and n8n HTTP coordination all call the same domain implementation. The [Phase 8 release test](docs/phase-8/DELIVERY-AUDIT.md) exercises the Python suite, MCP client and workflow exports from a clean extraction; [Phase 7](docs/phase-7/COMPLETION-AUDIT.md) supplies the connected engine and Odoo/Graph evidence. Changing model provider does not grant new permissions or bypass approval. OpenAI is the validated hosted V1 profile; Claude/Grok have adapter contracts without live API validation, and the tested local Qwen3 profile did not meet the quality gate.
