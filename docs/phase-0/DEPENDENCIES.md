# Dependency and boundary audit

Observed on 2026-10-08, Asia/Jakarta. These are local observations, not connected acceptance.

## Machine budget

Windows; Python 3.13.6; Node 22.19.0; Intel i7-13620H; physical RAM 16,868,962,304 bytes. NVIDIA query reports RTX 4050 Laptop GPU with 6,141 MiB VRAM (WMI's AdapterRAM is truncated, so use nvidia-smi).

Phase 0–6 budget: one backend worker, one UI build at a time, at most four unit-test threads. Target combined project process RAM under 2 GiB excluding local inference. Local model: one model resident, concurrency one, initial context 4k; choose model only after license/artifact/quality verification. Do not download or load a model until free memory is checked. Stop a project-owned heavy workload if available RAM drops below 2 GiB or the machine experiences sustained pressure; never stop another project's service.

Native Ollama is not on PATH. This does not prove it is absent elsewhere. Native inference validation is pending. Do not install PostgreSQL merely to avoid Docker; SQLite is only a durable local harness.

## Access inventory

User says access should already exist and asks for concrete needs when required. No matching OpenAI/Anthropic/xAI/Graph/Azure/Odoo/Ollama environment variable names were present in the inspected shell. No credential values were read or exposed. Project 04 has no supplied credential config yet. Do not copy credentials from sibling projects.

| Dependency | Required before | Current state / next action |
| --- | --- | --- |
| Microsoft 365 test mailbox | read-only canary Phase 4; connected Phase 7 | Need mailbox identity, app/client and tenant identifiers, authorized configuration location, consent and mailbox license confirmation |
| Graph delegated read | Phase 4 canary | Start with Mail.Read for message bodies; Mail.ReadBasic is insufficient for body extraction |
| Graph draft write / send | Phase 7 | Mail.ReadWrite for drafts; Mail.Send is separate; send remains disabled |
| Hosted model API | Phase 3 and 6 live evaluation | Need project-authorized key locations, accessible model IDs and a bounded spend budget; subscriptions alone are not API access |
| Ollama native | Phase 3/6 local evaluation | Runtime/artifact location unknown; installation and model budget pending |
| Odoo #2 test connection | Phase 7 | Contract exists; dedicated test database/company and scoped actors must be configured without touching working #2 data |

Microsoft permissions reference: https://learn.microsoft.com/en-us/graph/permissions-reference . Tenant consent policies may impose additional requirements. Delegated permissions are the initial single-operator design; unattended token lifecycle remains an explicit adapter requirement.

## Connector reuse

Project 02 HEAD `6a55b9dc61acd87e61b3aacb4da97d61af84b0fa`; `git status --short` returned no changes at audit. Inspect `backend/business.py`, `backend/contracts.py`, `backend/odoo_adapter.py`; consume APIs rather than copying their implementation.

The router exposes `/v1/opportunities`, `/v1/opportunities/{id}`, `/v1/activities/prepare`, proposal read/approve/execute and operation read/retry. ActivityInput is opportunity_id, assignee_id, YYYY-MM-DD due_date and summary (max 120, no angle brackets). Contract version 1.0 binds approvals to payload hashes; execution needs approval_id and idempotency_key. Results distinguish dispatched/unknown/verified/failed/review.

Mapping: project tenant -> configured connector tenant/company; deal external ID -> opportunity_id; assigned salesperson -> assignee_id; zoned due_at -> business-local date for Odoo activity, preserving full timestamp/timezone in project 04; summary must fit the connector constraint. Never silently truncate a meaning-bearing summary or guess an assignee. Recipient derives from verified contact mapping, never a model-provided arbitrary address.

General CRM field mutation is not exposed in the inspected contract. The first supported connected slice is an activity plus follow-up draft. Keep general field diffs reviewable but non-executable until a compatible connector capability exists. This gap does not silently remove the broader PHASES.md requirement. Project 04 approval must not manufacture approval inside #2: an authorized approver must bind the corresponding connector proposal before execution. Account linkage must be verified against connector customer/opportunity records.

## Versions and orchestration

Python app pins: FastAPI 0.142.4, Pydantic 2.13.5, HTTPX 0.28.1, Uvicorn 0.54.0, pytest 9.1.1. Resolve and freeze transitive dependencies in this project's isolated venv. Existing #2 pins provide compatibility context; registry resolution verifies availability.

n8n engine target: **2.42.5**, registry `npm view n8n version` result, no engine installation. Official release notes list 2.43 features but warn that publication does not guarantee availability: https://docs.n8n.io/changelog/release-notes.md . n8n owns scheduling/coordination only; authenticated outbound polling is the local design. Exact-tag node versions are verified in [N8N-MAPPING.md](N8N-MAPPING.md); image execution and complete export parameter validation remain pending.

MCP: protocol 2025-11-25 is an initial interoperability target; SDK selection and negotiated-version reference-client test remain pending. https://modelcontextprotocol.io/specification/2025-11-25

Native readiness and all provider/model versions are reported separately from PostgreSQL/n8n/Odoo/Microsoft 365 acceptance.
