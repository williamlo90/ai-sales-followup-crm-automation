# Project-scoped connector setup

This page explains project-scoped configuration. Connected sandbox acceptance was subsequently completed in [the Phase 7 audit](COMPLETION-AUDIT.md); copying these examples alone does not enable an external write. The release defaults remain off until the operator explicitly configures and approves a scoped action.

Copy deploy/connectors.example.json to ignored local/connectors.json and replace every placeholder with authorized project sandbox mappings. Remove an optional odoo/graph section if it is not selected. Set process variable SALES_CONNECTORS_PATH=local/connectors.json when launching the existing app factory. The local tenant and worker UUID must match the server identity file and PostgreSQL actors; mapped deals must be within that worker's allowed scope. Unknown flags, including send_enabled, are rejected.

- Odoo: connector #2 loopback URL, connector tenant, dedicated sandbox company/opportunity/assignee IDs and token file belonging to this authorized sandbox operator. Reuse its API contract; do not borrow unrelated production credentials or modify its live database.
- Graph: project test mailbox/folder, authorized token file and explicit message-ID-to-local-deal mapping. Store tokens only in project local/secrets; token reads happen when a request is made, so missing/expired tokens fail at the connector boundary. External refresh/provisioning is not implemented here.

All configuration/token paths are resolved under this project's local directory. No upward secret discovery. Token files are read afresh per request; neither composition nor startup makes network calls. No credentials should be pasted into chat or committed.

POST /v1/ingest/graph/poll is authenticated, accepts only the exact configured worker+tenant and processes one bounded Graph page atomically. Repeated pages remain idempotent; next-page scheduling belongs to the caller. Odoo connector-preparation/binding endpoints also check the configured local tenant before contacting the connector. CRM writes default to disabled. In the authorized sandbox configuration only, set the strict boolean crm_write_enabled=true to enable the existing execution and Odoo adapter. This still requires scoped identities, current local approval and an approved connector binding. Set false and restart to disable dispatch. Mail sending remains disabled regardless of this flag; send_enabled is rejected. Existing stored operations can be reconciled through read-only observation when properly scoped and configured.

The composition and denial tests remain regression coverage. For the connected Odoo read-back, Graph access, n8n execution and controlled-send evidence, use [the Phase 7 audit](COMPLETION-AUDIT.md); Graph send acceptance is not proof of recipient delivery.

For a fresh local install, supply only this project's authorized sandbox configuration and credential files. Begin with identity/read-only checks; remote state changes still require exact approval and current operator authorization.

## Personal Outlook account: initial read-only session

For a short interactive sandbox check, sign into [Graph Explorer](https://developer.microsoft.com/en-us/graph/graph-explorer) with the configured personal account. Consent to delegated User.Read and Mail.Read (the eventual ingestion reads message bodies). Copy the Access token tab's value into ignored local/secrets/graph-token, without a Bearer prefix. Do not put a Microsoft password or client secret there. This temporary developer session does not provide unattended refresh or application-owned OAuth registration.

Run `.venv/Scripts/python.exe -m scripts.graph_readiness`. The probe verifies /me against the configured mailbox before requesting at most one message ID through the adapter's /users addressing. It requests no body, follows no pagination, changes no database/checkpoint and prints only sanitized status/counts. Missing credentials fail before networking. Account aliases that do not match the returned profile fail closed and need explicit mapping verification. A passing probe proves only delegated identity and bounded read, not delta ingestion, send or end-to-end acceptance.

Sources checked 2026-10-10: [Graph Explorer features](https://learn.microsoft.com/en-us/graph/graph-explorer/graph-explorer-features), [personal-account User.Read](https://learn.microsoft.com/en-us/graph/api/user-get?view=graph-rest-1.0), [personal-account message delta permissions](https://learn.microsoft.com/en-us/graph/api/message-delta?view=graph-rest-1.0).

## Connected-lab model budget

For the accepted OpenAI profile set process variables OPENAI_MODEL=gpt-5.6-luna, OPENAI_REASONING_EFFORT=low, SALES_MODEL_ENABLED=true, SALES_MODEL_CALL_LIMIT=1 and SALES_MODEL_BUDGET_PATH=local/phase-6/budget.sqlite. Keep the API key in the existing project .env. The optional budget path must resolve inside this project's local directory; use the existing USD1 ledger so restarts do not reset its ceiling. The wrapper accepts only this priced profile, reserves before network access, limits input bytes/output allowance, and retains reservations when usage is unknown. It does not retry requests. Leave model execution disabled outside the bounded session.

Pricing rechecked 2026-10-10 against [official model documentation](https://developers.openai.com/api/docs/models/gpt-5.6-luna): USD0.20/M input and USD1.20/M output; reservations retain the conservative USD0.25/M input/cache-write rate used by Phase6. Budget reservations are conservative commitments, not billed cost.

## Operator review of n8n proposals

An operator scoped to the proposal deal may attach the approved connector binding to a worker-owned proposal only while its exact persisted worker job is awaiting approval. This grants no ownership transfer, local approval or execution. Other proposals keep owner-only binding. Delegation is checked again after remote validation; stale or changed jobs fail closed. The separate approver still approves the exact local payload before the worker executes. Operators use their own session in the existing binding form.
