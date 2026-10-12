# Local development

This guide starts the **offline SQLite demo** with external execution disabled. The connected PostgreSQL/n8n/Graph/Odoo sandbox was validated separately; use the [Phase 8 operator guide](phase-8/OPERATOR-GUIDE.md) for that deployment and the [Phase 7 audit](phase-7/COMPLETION-AUDIT.md) for its evidence.

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

## OpenAI configuration and bounded canary

The factory reads only this project's ignored `.env`; process environment overrides its four model keys. No parent configuration discovery or variable interpolation occurs. Set `OPENAI_API_KEY` locally. Normal API extraction also requires an explicit `OPENAI_MODEL`, `SALES_MODEL_ENABLED=true`, and `SALES_MODEL_CALL_LIMIT` from 1 to 10. The limit is per adapter/process lifetime, not a persistent spending allowance; leave disabled outside a supervised session.

Run `.venv/Scripts/python.exe -m scripts.model_canary` for a presence-only check. Explicit `--run` authorizes one synthetic request independently of the app enable switch, using `gpt-4.1-mini-2025-04-14` when the model is blank. A different model is rejected until its canary budget is defined. The command reserves `local/openai-canary.json` before the request and refuses every subsequent run, including after failure, with no automatic retries. Review any intentional new experiment and budget separately. It checks source evidence and expected semantics and exercises the shared proposal/draft core in a temporary database. It does not approve or dispatch actions. The canary snapshot is not a final model-selection decision.
