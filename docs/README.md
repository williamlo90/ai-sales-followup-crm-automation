# Documentation

| Start here | Purpose |
| --- | --- |
| [English sales walkthrough](phase-8/DEMO.md) | Synthetic conversation, proposal/draft, approval, Odoo outcome and recovery |
| [Operator guide](phase-8/OPERATOR-GUIDE.md) | Local install, credentials, activation, review, health, backup and rollback |
| [Case study](CASE-STUDY.md) | Business problem, implementation, measured results and limitations |
| [Security](../SECURITY.md) | Trust boundaries and responsible disclosure |

## Architecture and contracts

- [Sales domain and skills](../REUSABLE-SKILLS.md)
- [MCP server and reference client](../mcp-server/README.md)
- [n8n workflow exports](../automation/n8n/README.md)
- [Project-scoped connector configuration](phase-7/CONNECTOR-SETUP.md)
- [PostgreSQL runtime](phase-7/POSTGRES-RUNTIME.md)

## Validation evidence

- [Connected sandbox gate](phase-7/COMPLETION-AUDIT.md)
- [Combined Outlook OAuth journey](evidence/phase-7-outlook-oauth-connected.json)
- [Local delivery gate](phase-8/DELIVERY-AUDIT.md)
- [Final clean-install result](evidence/phase-8-release.json)
- [Phase 9 local-only decision](phase-9/DECISION.md)

The evidence describes synthetic local runs and the exact scope indicated in each report. It does not establish production uptime, customer ROI or cloud validation. Credentials and raw runtime state stay under ignored `local/`.
