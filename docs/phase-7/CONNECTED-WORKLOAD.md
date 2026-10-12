# Connected workload protocol

Declared before execution, 2026-10-10. Run one isolated profile session with PostgreSQL256MiB, Odoo512MiB, connector192MiB, n8n512MiB and the native application. Stop below768MiB host free RAM. Preserve sibling containers. No email sends or paid model calls.

| Profile | Work | Arrival |
| --- | --- | --- |
| Normal | 2 distinct CRM commitments | Next after previous verified |
| Peak | 3 distinct CRM commitments | Burst, bounded by request latency |
| Short soak | 4 distinct CRM commitments | One every30 seconds |

Each task uses shared HTTP ingestion/commitment/enqueue, actual n8n coordination, distinct operator/approver review, real Odoo prepare/approval/write/read-back and PostgreSQL ledger. Duplicate enqueue must preserve the job ID; each completion must have exactly one verified operation. Never retry a failed external write blindly. Abort a profile after360 seconds or on review/unknown/disabled outcomes; preserve partial results.

Freeze all nine distinct source messages before enqueuing work. Arrivals here are commitment jobs against that fixed source set. Streaming new source messages during approval is a separate freshness scenario: the first run correctly stopped with source_changed, five verified operations and no operation for the rejected job. Do not weaken freshness to make the workload pass.

Measure enqueue-to-verified p50/p90/p95, queue-to-proposal observation delay, errors, throughput and maximum outstanding jobs. Timing includes automated approval and one-second observation polling; small-N upper quantiles are descriptive, not capacity guarantees. Save raw samples locally. Success means every declared task verifies once with zero false success; latency is measured, not compared to the native500ms API SLO.

This isolates deterministic workflow load on the real n8n/API/PostgreSQL/Odoo stack. Input is seeded and model calls disabled; no claim about Graph/model latency, extraction quality or cost per correct AI task. n8n uses a declared10-second lab cadence to exercise the queue within the session budget; configured cadence is now three minutes. A four-task short soak cannot establish long-term reliability. The separate real OpenAI/PostgreSQL quality layer and one full connected path are mapped with these workload results in `COMPLETION-AUDIT.md`; Phase7F is closed for that layered scope.

Run `local/connected_workload_probe.py` using the project Python environment; it starts only the known isolated project04 sandbox and stops its owned services afterward. Test schemas, engine volumes and private runtime credentials remain under ignored local storage for diagnosis.
