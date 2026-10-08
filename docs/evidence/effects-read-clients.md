# Effect overlap and read clients

Validated 2026-10-09 Asia/Jakarta. `.venv/Scripts/python.exe -m pytest -q`: 132 passed; one existing Starlette TestClient deprecation warning. MCP TypeScript build and both native stdio suites passed.

## Effect policy

The same transaction now checks prior effects before inserting a dispatch record. A manual proposal sharing any source ID with an earlier operation requires review, including a switch to/from a bound proposal. This is independent of source revision and blocks both completed and unknown earlier outcomes. Exact logical-key replay retains the previous operation. A new bound commitment ID with identical source quotation also requires review; distinct bound commitments with distinct evidence can share a thread. Revised bound commitments after an operation continue to require update review because connector #2 does not expose an update contract.

Tests cover both manual/bound execution orders, known/unknown first outcomes, alias IDs and concurrent attempts. Concurrency evidence uses the serialized SQLite harness; PostgreSQL locking acceptance remains Phase 7. The rule is conservative for manual proposals: it may block a legitimate second action until the identity is resolved. It does not establish semantic equivalence between differently quoted commitments; human candidate review remains necessary.

## Read clients

`backend/read_clients.py` supplies injectable read-only Graph and Odoo #2 clients. They are not yet wired to an ingestion scheduler or live credentials. No network connection was made by this test batch; HTTP behavior uses boundary doubles.

Graph reads one mailbox/folder delta page per call. It requires tenant/mailbox-bound checkpoints, validates the exact Graph origin and collection path before sending credentials, preserves removal tombstones, requests immutable IDs/text bodies, and returns either continuation or completed-delta checkpoint. The caller must persist ingestion and checkpoint atomically; that orchestration is pending. Expired checkpoints request explicit resynchronization; there is no silent reset or automatic replay of old business actions. Multi-page cycle/workload limits remain a coordinator responsibility.

HTTP reads cap response size at 1 MiB and attempts at three. Numeric Retry-After up to 10 seconds is respected; longer or nonnumeric/date-form delays defer to the caller without early retry. Authentication rejection, redirects and transport failures do not retry. Token providers are injected, and token-provider errors are sanitized. OAuth acquisition/refresh and live consent are pending.

Odoo reads `/me` and `/v1/opportunities` or `/v1/opportunities/{id}` from a configured loopback connector. Tenant, company, source, record ID and version are checked. Connector #2 currently caps its opportunity collection at 100 and provides no pagination; this client does not invent cursor support. It never calls the approval, prepare, execute or retry endpoints. Write/reconciliation binding and approved company/test-record mapping remain pending.

Contracts inspected read-only in project #2: `backend/business.py`, `backend/contracts.py`, `odoo/addons/ops_bridge/models.py`. Graph behavior references [message delta](https://learn.microsoft.com/en-us/graph/api/message-delta?view=graph-rest-1.0) and [throttling guidance](https://learn.microsoft.com/en-us/graph/throttling). No sibling repository changes, email sends or containers were used.
