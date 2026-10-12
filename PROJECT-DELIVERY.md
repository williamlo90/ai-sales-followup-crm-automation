# Local V1 delivery

The product turns a sales conversation into a source-backed CRM proposal and follow-up draft. The sales operator checks the source, customer, date, diff and recipient; a separate approver authorizes the exact action. n8n coordinates the queue and schedule, while the Python domain owns permissions, freshness, approval and effect reconciliation.

The delivery package is `local/releases/sales-followup-local-v1.zip`. Its manifest identifies every file in the source snapshot. The archive contains pinned source/dependencies, synthetic fixtures, inactive n8n exports and the documentation below; project credentials and runtime data remain outside it.

- [Operator guide](docs/phase-8/OPERATOR-GUIDE.md): installation, credentials, activation, daily review, health, incident response, backup/restore and rollback.
- [English demo](docs/phase-8/DEMO.md): synthetic conversation → proposal/draft → separate approval → Odoo read-back → recovery.
- [Delivery audit](docs/phase-8/DELIVERY-AUDIT.md): clean extraction, test/import results, support drill and limitations.
- [Case study](docs/CASE-STUDY.md): measured results and integration/model scope.
- [Phase 7 audit](docs/phase-7/COMPLETION-AUDIT.md): connected-sandbox evidence and its boundaries.

The local owner keeps the Outlook/Graph and Odoo sandbox mappings, access tokens, OpenAI budget, n8n encryption key, PostgreSQL credentials and backups. Workflow activation, human review and recovery are operator decisions. A laptop that sleeps or disconnects stops scheduled work until the stack returns; persistent queues/checkpoints allow catch-up and prevent blind resend. This is local delivery, not a 24-hour hosted service or a customer production-support contract.

Phase 9 cloud deployment and Make.com/Zapier variants are optional extensions. The user selected local V1 and declined those extensions for this release.
