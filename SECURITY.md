# Security

This is a loopback-first local sales automation lab. The offline demo uses synthetic data and cannot execute external effects. Do not expose its development API, UI or n8n instance to the public internet.

## Boundaries

- Actor identity, tenant/deal scope and worker role are bound server-side. Model and MCP arguments cannot grant authority.
- CRM and email approvals are independent and tied to the exact proposal version and payload. A changed source invalidates stale approval.
- External writes use a durable operation identity. Unknown outcomes require target observation before any retry; accepted email is not proof of delivery.
- Graph/Odoo credentials are project-local files. Model calls use an explicit profile, request limit and persistent budget ledger. Sending is off by default.
- Browser session tokens remain in memory and are cleared on sign-out. The synthetic demo token file is ignored by Git.

## Credentials and publication

Never commit `.env`, `local/`, access tokens, encryption keys, database volumes, real customer messages or private model output. `.env.example` contains blank key values. Public evidence uses synthetic cases and sanitized metrics. The CI checks forbidden paths and scans the entire Git history with a pinned Gitleaks binary. A clean scan is a useful control, not a guarantee that arbitrary private data cannot appear.

Before publishing changes, run `python scripts/check_publication.py`, `python -m pytest -q`, the UI/MCP builds, and a secret scan. Keep any real Graph token or Odoo credential in ignored project-local files; do not paste it into an issue, log or screenshot.

## Report a vulnerability

Use GitHub's private vulnerability reporting under **Security** where available. Include the affected revision and a synthetic reproduction. Do not post credentials or private mailbox content in a public issue. If private reporting is unavailable, contact the repository owner through the GitHub profile without attaching sensitive payloads.
