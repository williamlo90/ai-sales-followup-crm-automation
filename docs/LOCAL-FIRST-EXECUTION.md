# Local execution rules

The delivered V1 runs on the owner's laptop and uses project-scoped sandbox data. Start with native tests and read-only checks. Enable real connectors only for the configured test mailbox and Odoo sandbox, with separate human approval for writes.

The local PostgreSQL service is capped at 256 MiB and n8n at 512 MiB in `deploy/compose.yaml`. Check available host memory before running them. Manage only this project's containers, volumes and ports; never stop or restart another project's stack as a cleanup shortcut. Keep `.env`, tokens, encryption keys, database volumes and raw run logs under ignored `local/`.

The operator follows the [handover guide](phase-8/OPERATOR-GUIDE.md) for startup, credentials, review, monitoring, backup and rollback. A sleeping/offline laptop pauses schedules; persisted jobs and operation records support bounded catch-up after restart. The [Phase 7 audit](phase-7/COMPLETION-AUDIT.md) describes what was actually validated and what remains outside the local V1 scope.
