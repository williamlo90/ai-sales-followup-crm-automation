# Connected acceptance handoff (not executed)

Phase 6 preparation only. Native evaluation candidate is frozen in candidate-freeze.json under OpenAI-only V1; connected release is not accepted. No row below is connected-validated. Existing native tests exercise the shared business core with SQLite and boundary doubles.

| Acceptance | Existing native evidence | Required Phase 7 observation |
| --- | --- | --- |
| PostgreSQL data and isolation | Store/domain unit tests; static migrations | Implement repository/transaction composition; apply migrations to isolated database; verify RLS, concurrent claims, rollback and restart with actual PostgreSQL. SQLite cannot close this row. |
| Odoo contract #2 | read_clients, odoo_effects and bindings tests | Dedicated test database/company, verified record mapping, remote approval/snapshot, real update and read-back; no project #2 production data changes. |
| Graph intake | ingestion/read_clients tests | Project test mailbox and scoped permission; initial/delta reads, folder boundaries, deleted messages, expired cursor and replay. |
| n8n intake and due exports | workflow_exports reference traversal | Import pinned engine; verify inactive-to-enabled test workflow, credentials, actual schedule/Wait/resume/restart and final effect counts. |
| Approval and freshness | foundation, execution, handoff tests | Real operator/approver separation; source/CRM revision changes invalidate approvals; expired proposal renewal needs fresh approval. |
| Send and recovery | graph_effects, execution, workflow_recovery tests | Explicit lab send authorization and allowlist; accepted/sent/received evidence separately; lost response observed before retry, no duplicate send. |
| Partial effects | execution/effect_overlap tests | CRM success plus email unknown remain separate across process/engine restart, with one logical effect. |
| Performance and resources | 100-operation native workload only | Measure final concurrent stack, normal/peak/soak, queue age, errors, throughput, host RAM/CPU, model residency and cost per correct task. |
| Operations | Static configuration/runbooks | Isolated DB and n8n state backup/restore including encryption config; clean import, rollback, Linux reboot and observed alert delivery. |

Before any Phase 7 launch: inventory active workloads read-only, choose isolated project name/ports/data and explicit session resource limits. No global cleanup, stopping sibling services or shared volumes. Run components sequentially where possible; final vertical slice still requires its minimum components simultaneously. Missing resources remain blocked rather than replaced with mocks or cloud provisioning.

Open dependencies for OpenAI-only V1: PostgreSQL/connector composition, Microsoft 365 and Odoo sandbox mappings. Local Qwen3 inference was evaluated and rejected (0/20); both single-operator worksheet sessions are recorded, including live local core waiting. Neither result establishes connected acceptance. These dependencies are not satisfied by this matrix.
