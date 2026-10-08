# Local development

Current slice: authenticated preparation and independent CRM/email approval, durable SQLite harness, React review UI. External execution and model extraction are not implemented in this slice. The UI displays that limitation. PostgreSQL is the target persistence layer; SQLite results are not PostgreSQL evidence.

From the project directory in PowerShell:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r backend/requirements.lock
npm.cmd ci --prefix web
.venv/Scripts/python.exe -m pytest -q
npm.cmd run build --prefix web
```

Create local synthetic data and random scoped credentials once:

```powershell
.venv/Scripts/python.exe -m scripts.seed_demo
$env:SALES_IDENTITIES_PATH = 'local/identities.json'
.venv/Scripts/python.exe -m uvicorn backend.app:from_environment --factory --host 127.0.0.1 --port 8040
```

In a second terminal, run `npm.cmd run dev --prefix web` and open http://127.0.0.1:8044. Access tokens are in ignored `local/access-tokens.json`: operator prepares, approver reviews, auditor reads. Keep tokens private. Tokens exist only in UI memory and are cleared on sign-out; this is a local development auth profile, not production identity lifecycle. The worker token is for trusted ingestion and is not required by the UI.

Both proposed actions require separate approval. Recording approval does not run external actions. Source quotes are checked against the ingested source; semantic accuracy of human-supplied drafts still requires human review. Do not call this LLM validation.

Browser acceptance uses installed Microsoft Edge, a temporary database and test-only identities:

```powershell
npm.cmd run test:e2e --prefix web
```

Ports 8040/8044 must be free. The browser test refuses to reuse an existing server and does not stop unrelated processes. Stop your own dev servers before running it. A restart preserves the local SQLite database but never makes it a connected integration.
