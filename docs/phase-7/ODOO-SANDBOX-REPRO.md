# Reproduce the Odoo sandbox boundary

Project 04 consumes the public business API from [project 02](https://github.com/williamlo90/odoo-business-operations-mcp-server). The inspected producer revision was [`44b03db`](https://github.com/williamlo90/odoo-business-operations-mcp-server/tree/44b03db0f60c15dc389a43e6f9e18765f83ea455), with [business API contract 1.0](https://github.com/williamlo90/odoo-business-operations-mcp-server/blob/44b03db0f60c15dc389a43e6f9e18765f83ea455/docs/CONTRACT-V1.md). Its API contract files were unchanged since the original Phase 0 audit at `6a55b9d`. Use this revision to reproduce the documented boundary; check the upstream contract and fixtures before intentionally upgrading it. Project 04 calls the API and does not copy project 02's source or database.

This path needs Docker Desktop with Linux containers, Python 3.13, Node 22, enough resources for Odoo/PostgreSQL, and free loopback ports 8020 and 8069. The offline project 04 review demo needs none of these. Use a **fresh dedicated clone** of project 02 and its own Compose project/volumes; do not point Sales at another project's active database or credentials. The commands below start only that dedicated clone. If the default ports are occupied, change `API_PORT` and the Odoo host port in the clone's private configuration before startup, and use the resulting API port in project 04.

```powershell
git clone https://github.com/williamlo90/odoo-business-operations-mcp-server.git sales04-odoo-sandbox
cd sales04-odoo-sandbox
git checkout --detach 44b03db0f60c15dc389a43e6f9e18765f83ea455
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r backend/requirements.lock
.venv/Scripts/python.exe deploy/setup_env.py
.venv/Scripts/python.exe deploy/setup_odoo_env.py
$env:COMPOSE_PROJECT_NAME = 'sales04-odoo-sandbox'
docker compose -f compose.yaml -f compose.odoo.yaml -f compose.resources.yaml build
docker compose -f compose.yaml -f compose.odoo.yaml -f compose.resources.yaml up -d --wait --wait-timeout 300 api
```

The first check is read-only: open `http://127.0.0.1:8020/health/ready` and expect `ready`. Then sign in to `http://127.0.0.1:8020/` as the synthetic `operator.a` using `DEMO_PASSWORD` from that clone's private `.env`; inspect an opportunity without preparing or executing an activity. Alternatively, call `POST /auth/login` and then `GET /v1/odoo/info` and `GET /v1/opportunities` with its short-lived bearer token. The [producer operator guide](https://github.com/williamlo90/odoo-business-operations-mcp-server/blob/44b03db0f60c15dc389a43e6f9e18765f83ea455/docs/USER-GUIDE.md) covers login and seed data. A healthy API alone does not prove an approved write.

From the project 04 checkout, copy `deploy/connectors.example.json` to ignored `local/connectors.json`. Set `odoo.base_url` to the dedicated project's API loopback URL (default `http://127.0.0.1:8020`), its actual connector tenant/company, opportunity and assignee IDs, and a project-04-local `local/secrets/odoo-token` holding a scoped sandbox session. Replace all example UUIDs and deal mappings with the matching project 04 identity/deal records. Keep `crm_write_enabled=false` for the initial read-only check. `GET /v1/odoo/info` and the opportunity detail must match the configured company and deal before enabling an approved write. Project 04's [connector setup](CONNECTOR-SETUP.md) explains the subsequent approval/binding path; the [operator guide](../phase-8/OPERATOR-GUIDE.md) explains the rest of the local stack. No secret belongs in Git or a chat message.
