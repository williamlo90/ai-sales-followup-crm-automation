# reconcile_followup — 1.0

Owner: Sales Operations. Binding: `SkillService.reconcile_followup`; input: input.schema.json. Result: operation fields, recovery, observation and adapter_available.

Use to inspect an existing operation, especially dispatched/unknown results. Never use to repeat a send. First verify tenant/deal scope. If an adapter is configured, operator/worker may observe it and update the operation's evidence-backed outcome. Otherwise return stored_only and adapter_available=false; do not claim a fresh platform read.

Example: `{"operation_id":"operation-uuid"}`. Adapter evidence must match operation, tenant and payload hash. A CRM read-back can verify CRM completion. Mail acceptance or Sent Items remains accepted, never delivered/read. Reconciliation remains allowed after proposal expiry because observation must not be blocked by stale execution authority. No dispatch/retry tools. Common errors and bounded operation rules: ../README.md.
