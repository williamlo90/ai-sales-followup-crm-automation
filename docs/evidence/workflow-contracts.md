# Workflow queue and export contracts

2026-10-09 Asia/Jakarta: 201 Python tests passed; two native MCP suites passed. Existing Starlette TestClient deprecation warning remains.

Implemented a durable job queue, worker ownership and scope, deterministic enqueue identity, leased claim, shared-skill proposal preparation, separate approval polling, due checks, default-off dispatch, operation checkpoint and read-only reconciliation. The coordinator holds no database transaction across adapter calls. Unknown outcomes never trigger a second dispatch; unresolved observations enter review. Static PostgreSQL migration 006 prepares the queue and tenant policy without engine execution.

Tests include duplicate enqueue, role/tenant denial, concurrent ticks, independent CRM/mail approval, due-time hold, stale sources, restart after an unknown operation and a crash after effect dispatch before the job update. Both n8n JSON exports match their generator. A bounded reference traversal calls the real local API and verifies intake prepare/wait/approve/execute and due hold against an effect double. Simulated wait is explicitly not engine wait evidence.

Commands: `.venv/Scripts/python.exe -m pytest -q --tb=short`; `npm.cmd test --prefix mcp-server`; `.venv/Scripts/python.exe -m scripts.export_workflows`; `git diff --check`.

Node versions are pinned in docs/phase-0/N8N-MAPPING.md. HTTP auth/timeout parameter names were checked against the [2.42.5 HTTP node source](https://raw.githubusercontent.com/n8n-io/n8n/n8n%402.42.5/packages/nodes-base/nodes/HttpRequest/V3/Description.ts); wait parameters against the [Wait node source](https://raw.githubusercontent.com/n8n-io/n8n/n8n%402.42.5/packages/nodes-base/nodes/Wait/Wait.node.ts).

Current input is a reviewed commitment. Automatic source-to-candidate-to-queue handoff, due discovery, job recovery UI and engine acceptance remain incomplete. The exports are workflow-designed/endpoint-contract-validated, not n8n-validated. No engine/container, actual provider, Odoo/Graph write or email send was run.
