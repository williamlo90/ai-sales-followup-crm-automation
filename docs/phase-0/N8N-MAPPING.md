# n8n target contract

Engine pin 2.42.5; bundled nodes-base 2.42.3 (`npm view n8n@2.42.5 dependencies.n8n-nodes-base`). This is a source/schema decision, not an engine run.

| Node | Selected version | Purpose |
| --- | --- | --- |
| n8n-nodes-base.scheduleTrigger | 1.4 | Authenticated outbound intake/due polling; Asia/Jakarta |
| n8n-nodes-base.httpRequest | 4.5 | Custom backend endpoints; header credential reference, bounded timeout |
| n8n-nodes-base.if | 2.3 | Route authoritative backend statuses |
| n8n-nodes-base.wait | 1.1 | Timed approval polling without a public resume webhook |

Versions verified against the exact source tag:

- https://raw.githubusercontent.com/n8n-io/n8n/n8n%402.42.5/packages/nodes-base/nodes/Schedule/ScheduleTrigger.node.ts
- https://raw.githubusercontent.com/n8n-io/n8n/n8n%402.42.5/packages/nodes-base/nodes/HttpRequest/HttpRequest.node.ts
- https://raw.githubusercontent.com/n8n-io/n8n/n8n%402.42.5/packages/nodes-base/nodes/If/If.node.ts
- https://raw.githubusercontent.com/n8n-io/n8n/n8n%402.42.5/packages/nodes-base/nodes/Wait/Wait.node.ts

Schedule uses rule.interval entries with field=minutes and minutesInterval=5. Wait uses resume=timeInterval, amount=60, unit=seconds. API nodes use a configured service credential; exports never embed tokens. HTTP request parameter details must be checked when exports are authored in Phase 5.

Endpoint plan (not yet all implemented): intake claim/prepare; due eligibility; proposal read for approval wait; CRM apply; reconciliation. Each has a bounded item batch and checkpoint. Workflow actions use server-owned tenant/deal scope. Retry read-only calls at most three times with bounded backoff; reconcile unknown writes/sends before any retry. Phase 7 proves import, wait persistence, restart, credential binding and failure routing.

Budget: one execution and one model request at a time; 60-second approval polling; proposal expiry 24 hours. Retain sanitized engine history for 72 hours. Restore n8n state and its encryption key together. Secrets stay outside Git. Static deploy/compose.yaml is preparation, not permission to start it in this loop.
