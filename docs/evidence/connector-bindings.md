# Durable connector bindings

The binding repository persists a local proposal/hash against the connector tenant, operator, proposal, approval and exact activity preview. A binding is immutable and a remote tenant/proposal pair may belong to only one local proposal. The proposer must attach it; approvers/auditors can inspect scoped bindings but cannot attach them.

Attachment validates current local evidence, performs the adapter's read-only workspace/approval checks, refuses an already-executed connector proposal, then rechecks local freshness before inserting the binding and audit event in one transaction. Source changes during the remote read roll back attachment. A scoped payload loader supplies immutable historical content for mail reconciliation even after proposal expiry; this does not renew execution authority.

HTTP routes: `GET/POST /v1/proposals/{id}/connector-binding`. The normal app factory has no connector configured, so attachment returns `connector_not_configured` without an external call. When explicitly configured, attachment writes only the local binding and reads the connector. It does not grant either local or connector approval. There is no LLM/MCP binding-attachment tool.

Native tests cover restart/replay, uniqueness, replacement rejection, mid-validation source changes, role/tenant scope, expired observation data, refusal to adopt executed proposals and HTTP default-off/read access. The tests use a connector HTTP double; they do not establish a live Odoo binding. Migration `005_connector_bindings.sql` prepares the PostgreSQL unique constraints/RLS for later engine acceptance.

Validation on 2026-10-09 Asia/Jakarta: Python suite 190 passed; both native MCP suites passed. Existing Starlette TestClient deprecation warning remains. No connected calls, model spending, email sends or containers occurred. Connector proposal creation and binding UI remain pending; normal application execution is still disabled.
