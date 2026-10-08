# Native MCP and shared skill contracts

Validated 2026-10-09 Asia/Jakarta:

- `.venv/Scripts/python.exe -m pytest -q`: 107 passed; existing Starlette HTTPX TestClient deprecation warning remains.
- `.venv/Scripts/python.exe -m scripts.export_skill_schemas`: four complete skill output contracts plus context/operation schemas generated. Regression test compares checked-in skill schemas against Python contracts.
- `npm.cmd run build --prefix mcp-server`: TypeScript compilation passed.
- `npm.cmd test --prefix mcp-server`: two suites passed. Real SDK client/server negotiated `2026-07-28` over stdio, with the same Python domain and temporary SQLite storage behind native HTTP.

Covered: seven tools discovered; scoped context; extraction using a labeled model double; bound proposal preparation and replay; draft; cross-tenant and wrong-role denial; invalid argument rejection; stale source invalidation; disabled external actions; missing operation handling; bounded output; sanitized upstream errors; cancellation followed by a usable client. Python API tests separately inject the existing effect double to verify approval enforcement, unknown-outcome replay and read-back without duplicate dispatch.

No live model request was made in this batch. No Odoo/Graph/n8n connection, email send, Docker execution or PostgreSQL runtime validation occurred. Execution tools are exposed but disabled in normal configuration. Phase 4 still needs concrete business clients, deeper protocol failure cases and the connected acceptance handoff; no complete phase gate is claimed.
