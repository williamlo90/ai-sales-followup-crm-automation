# Sales workflow exports

Two inactive definitions target n8n 2.42.5 / nodes-base 2.42.3: `intake-v1.json` and `due-v1.json`. They schedule a backend tick every five minutes, inspect its `needs_poll` flag, wait 60 seconds when requested, then perform one additional tick. Each execution ends after at most two requests; subsequent schedules continue the durable backend queue. There is no public resume webhook or automatic HTTP POST retry.

Before Phase 7 import, replace `http://sales-domain:8040` with the isolated backend address reachable by n8n. Bind the placeholder header credential `CONFIGURE_SALES_WORKER` to `Authorization: Bearer <scoped worker token>` in the engine's credential store. No secret is embedded. Use the same worker identity that owns queued jobs. Configure engine concurrency one, history retention 72 hours and the existing isolated encryption/state profile. Keep both workflows inactive until the Phase 7 acceptance session.

The current queue entry boundary is a reviewed, recorded commitment candidate. Source ingestion, model extraction and candidate review are upstream; automatic discovery/enqueue of those events remains pending. A trusted worker posts this shape to `/v1/workflows/jobs`:

```json
{"deal_id":"deal-1","deal_version":1,"commitment":{"id":"c1","revision":1},"journey":"intake","kind":"crm"}
```

Use `journey: due` for due-follow-up coordination and `kind: email` for approved mail. One job represents one effect; CRM/email approvals and outcomes remain separate. Duplicate enqueue returns the same job. Shared `prepare_crm_update` produces the proposal; an independent human grants approval through the existing review flow. n8n never generates an approval.

Backend ticks delegate freshness, opt-out, due eligibility, dispatch ledger and reconciliation to the shared core. Each tick claims at most one job with a two-minute lease and schedules a follow-up no sooner than 60 seconds. A crash after dispatch is recovered through the operation ledger. Unresolved observation, stale context or expired proposal moves to review; it does not resend. Normal configuration has no execution adapter and reports disabled. The workspace recovery panel explicitly requests observation, prerequisite recheck or expired-proposal renewal. A terminal review job is not silently reset.

`GET /v1/workflows/jobs/{id}` exposes scoped status for review clients. The two workflow tick endpoints require worker role and select only jobs owned by that identity. A polling node advances the next eligible job, which can differ from the preceding job; the backend queue owns correlation and fairness.

Generate with `.venv/Scripts/python.exe -m scripts.export_workflows`. `tests/test_workflow_exports.py` validates definitions and traverses them through the actual FastAPI/domain using a small contract runner and simulated time. This is not an n8n engine emulator, import validation, wait persistence proof or connected acceptance. Due ticks now discover latest eligible commitments through a bounded persisted cursor. Future due jobs wait before proposal preparation. Engine import/execute/restart, upstream intake handoff and real PostgreSQL concurrency remain open gates.
