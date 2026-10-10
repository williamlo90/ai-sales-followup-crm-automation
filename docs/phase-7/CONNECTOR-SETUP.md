# Project-scoped connector setup

Composition is implemented and tested; Odoo/Graph live acceptance is not established by this setup. No email or CRM mutation is enabled. Read-only service calls may update the local ingestion database.

Copy deploy/connectors.example.json to ignored local/connectors.json and replace every placeholder with authorized project sandbox mappings. Remove an optional odoo/graph section if it is not selected. Set process variable SALES_CONNECTORS_PATH=local/connectors.json when launching the existing app factory. The local tenant and worker UUID must match the server identity file and PostgreSQL actors; mapped deals must be within that worker's allowed scope. Unknown flags, including send_enabled, are rejected.

- Odoo: connector #2 loopback URL, connector tenant, dedicated sandbox company/opportunity/assignee IDs and token file belonging to this authorized sandbox operator. Reuse its API contract; do not borrow unrelated production credentials or modify its live database.
- Graph: project test mailbox/folder, authorized token file and explicit message-ID-to-local-deal mapping. Store tokens only in project local/secrets; token reads happen when a request is made, so missing/expired tokens fail at the connector boundary. External refresh/provisioning is not implemented here.

All configuration/token paths are resolved under this project's local directory. No upward secret discovery. Token files are read afresh per request; neither composition nor startup makes network calls. No credentials should be pasted into chat or committed.

POST /v1/ingest/graph/poll is authenticated, accepts only the exact configured worker+tenant and processes one bounded Graph page atomically. Repeated pages remain idempotent; next-page scheduling belongs to the caller. Odoo connector-preparation/binding endpoints also check the configured local tenant before contacting the connector. Execution/router and mailbox adapters are composed but writes/sends remain disabled in this version. Existing stored operations can be reconciled through read-only observation when properly scoped and configured.

Validation:7 composition tests pass, including missing-token startup without access, invalid tenant/worker/mapping, outside-project token path, attempted send enable and wrong-worker polling denial. Real PostgreSQL ingestion/operation-ledger acceptance used simulated Graph and effect adapters. This does not prove vendor authentication, Odoo read-back, Graph delivery, or n8n engine execution.

Next connected input: the authorized sandbox configuration path, or confirmed mappings and credential files within this project's local directory. Begin with identity/read-only tests; remote state changes and email require the separate controlled acceptance steps.
