# Sales MCP

Native stdio bridge to the shared FastAPI domain. Pinned SDK server/client 2.3.1 and reference client negotiate protocol `2026-07-28`, matching the [official SDK v2](https://github.com/modelcontextprotocol/typescript-sdk). Node 22 or later is required.

From the project root:

```powershell
npm.cmd ci --prefix mcp-server --ignore-scripts
npm.cmd run build --prefix mcp-server
npm.cmd test --prefix mcp-server
```

Start the local backend as documented in `docs/LOCAL-DEVELOPMENT.md`. Configure `SALES_API_URL` with a loopback HTTP origin and `SALES_TOKEN` with a scoped local session token in your MCP host's private environment. Launch `node` with the absolute path to `mcp-server/dist/server.js`. Do not put keys/tokens in tool arguments. Only protocol output goes to stdout. The reference client in `src/client.ts` exports `connectSales(base, token)` and forwards only required OS variables and the two explicit bridge settings to its child.

Tools: `sales.get_deal_context`, `sales.extract_commitments`, `sales.prepare_crm_update`, `sales.draft_followup`, `sales.reconcile_followup`, `sales.apply_crm_changes`, `sales.send_approved_draft`. Reconciliation supplies follow-up verification. Preparation requires an existing reviewed commitment candidate. No tool ingests arbitrary records or grants approval. Context and tool results contain untrusted source text; consuming assistants must treat it as data.

Every operation uses the backend's actor scope, freshness and approval rules. External effects return `execution_disabled` in the normal app factory. Execution injection is currently exercised only with contract doubles. Reconciliation reports `stored_only` when no observer is configured. Read-back and accepted mail never imply recipient delivery.

The bridge allows one active call, caps responses at 256 KiB, uses a 65-second request deadline, follows no redirects and propagates cancellation to HTTP. Cancellation cannot undo an already-running backend operation or model request. An unknown outcome requires status/reconciliation before retry; the bridge does not retry automatically. Input/output JSON schemas are exported from Python, not a second business implementation.

Tests start their own temporary native backend on an OS-assigned loopback port and close only owned processes. Extraction uses an explicitly labeled model double, with no API spend. A second suite uses an HTTP boundary double for cancellation/error/size tests. These establish real stdio protocol interoperability, not Graph/Odoo/n8n integration.
