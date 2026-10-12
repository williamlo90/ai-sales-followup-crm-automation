# Phase 9 extension decision

**Owner decision, 2026-10-12:** deliver the local V1. Cloud hosting for continuous 24-hour scheduling and Make.com/Zapier variants are not selected. No cloud resources, SaaS workflows, accounts, fees or production support service were created in Phase 9. The release status remains **local-delivered / connected-sandbox-validated**, with n8n as its single automation engine.

If continuous uptime or shared access becomes necessary, reopen Phase 9 as a separate deployment change. First select the hosting owner and budget, persistent PostgreSQL/n8n state, OAuth refresh and secrets management, alerts, backups, access controls and rollback. Only then deploy and rerun connected workflow, authorization, quality, bounded-load and recovery acceptance in that environment. The local evidence must not be represented as cloud validation.

If an alternate automation engine becomes valuable, choose one of Make.com or Zapier, run it against the same domain API and permissions with n8n disabled for the test tenant, and compare correctness, recovery, handover and cost. Neither variant is part of this V1 acceptance or release package.
