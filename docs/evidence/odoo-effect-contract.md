# Odoo activity effect contract

`backend/odoo_effects.py` implements the effect boundary against project #2's existing activity/workspace/operation HTTP contracts. It neither duplicates the Odoo server nor exposes an approval route. The normal app factory does not instantiate it and external execution remains off.

A trusted binding provider must resolve the immutable local proposal/hash to connector tenant, operator, proposal, approval and exact activity preview. A separately configured deal map fixes opportunity and assignee IDs. The adapter checks company, due date in the configured IANA timezone, exact summary within the connector's 120-character limit, source version, preview hash, independent approver and expirations. It does not truncate a summary or reinterpret a mismatched preview. Windows installations now pin `tzdata==2026.5` for timezone support.

Dispatch uses the local operation UUID as the connector idempotency key and calls the existing execute route once. It does not call approve or retry. If the workspace already contains an operation, it validates its identity instead of issuing a second POST. On lost response, observation discovers the operation through the bound workspace and reads `/v1/operations/{id}`. Observation works after approval expiry and never dispatches an absent operation. Unknown/dispatched/nonverified responses remain unknown locally.

A verified receipt must match operation ID, connector proposal/approval/tenant/idempotency key, preview hash and all activity record fields. Only then is it translated into the local receipt with `read_back_verified`. An HTTP success or an unrelated record cannot close the local operation.

Native HTTP-boundary tests cover normal execution/observation, lost response, absent operation, wrong opportunity/assignee/date/summary, changed source preview, wrong approval hash/tenant, self-approval, expiry, wrong record/idempotency/receipt hash, disabled writes, expired observation, unknown replay and oversized summary. These are contract doubles only. No request reached Odoo and no connected mutation occurred.

Pending: persistent immutable binding storage and binding review UI, connector proposal creation flow, approved dedicated test-company mapping, dispatch activation and real connected acceptance in Phase 7. Graph effect adapter and routing remain independent outstanding work. The prepared adapter is not a claim that Phase 4 is complete.

Validation on 2026-10-09 Asia/Jakarta: `.venv/Scripts/python.exe -m pytest -q` → 163 passed, including 18 Odoo adapter cases; existing Starlette TestClient deprecation warning remains.
