# Foundation verification — 2026-10-09 (Asia/Jakarta)

Environment: Python 3.13.6, Node 22.19.0, Windows, isolated project venv and npm dependency lock. All outcomes below are local harness/browser results.

| Command | Observed result |
| --- | --- |
| `.venv/Scripts/python.exe -m pytest -q` | 29 passed; one upstream Starlette HTTPX deprecation warning |
| `.venv/Scripts/python.exe -m pip check` | No broken requirements |
| `npm.cmd run build --prefix web` | TypeScript check and Vite production build passed |
| `npm.cmd run test:e2e --prefix web` | One browser scenario passed in installed Edge, including desktop and mobile assertions |
| `npm.cmd install --no-fund` in web | 24 packages installed; audit reported zero vulnerabilities at install time |

Backend cases cover separate approvals, durable restart, unauthorized roles, same actor with changed role, tenant and deal scoping, changed CRM/source revisions, expiry, proposal renewal without inheriting approval, concurrent duplicate proposals, forbidden authority fields, source quote validation, opt-out, already contacted, deleted deal, ingestion role, revision regression, timezone requirement, response redaction and hash mismatch. These do not prove external-effect deduplication because external dispatch is not yet implemented.

Browser case: invalid login -> operator login -> prepare synthetic proposal -> inspect source/recipient -> verify operator has no approval control -> sign out -> approver login -> separate CRM and email approvals -> verify no external action -> 390px layout without horizontal overflow -> sign out clears token. Screenshot `local/browser-review.png` was inspected visually. Browser test uses a temporary database and its own servers, not the user's dev database.

Static PostgreSQL migration, Dockerfile and Compose are prepared but have not run. No Docker command, model API, Graph mailbox operation, Odoo operation or external email send was performed. Native model/runtime and live provider validation remain pending.

Known remaining foundation work: PostgreSQL repository wiring and migration runner, full session lifecycle for deployment, typed adapter doubles and operation execution/reconciliation. Phase 1 is therefore in progress, not fully passed. Phase 2 adds matching/commitment revisions and final-effect invariants; source substring checks alone are not semantic draft verification.
