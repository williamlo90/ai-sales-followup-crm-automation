# Earlier-phase gap audit - 2026-10-10

| Area | Verified current state | Next action |
| --- | --- | --- |
| PostgreSQL | App factory uses SQLite Store. Static migrations use tenant_id UUID/JSONB; runtime SQL uses tenant/text payloads. requirements.lock has no PostgreSQL driver. Adding a DSN alone cannot wire these together. | Implement explicit repository/transaction mapping plus tenant context and error handling; contract tests first, real database acceptance remains separate. |
| Execution composition | from_environment supplies identities, SQLite and optional OpenAI only. No connector/execution adapter is composed. | Explicit disabled-by-default configuration and scoped mappings before connected acceptance. |
| OpenAI | Key present (value never printed); model ID absent, application model disabled. Previous canary reservation exists. | Keep app disabled and old reservation intact. Separate bounded Phase 6 runner after dataset/price/budget checks. |
| Other hosted providers | Adapters implemented; no project-scoped live acceptance established. | Request authorized configuration when comparison is ready; never reuse sibling secrets. |
| Native runtime | ollama and postgres not found on PATH in this check. | Not proof they are uninstalled. Locate authorized runtime later; do not install or launch containers during this audit. |
| Dataset | Eight development families; no held-out set. Preflight JSON reports failure and zero quality evaluation. | Author remaining independent families and review labels before freeze. |
| Phase 5 | Native gate evidence exists; definitions/UI tests do not close runtime/connected gaps. | Preserve scope of those claims. |

No Docker, connected write, email, model call, or secret discovery outside this project's configuration was performed. Automation remains PAUSED.


## Local runtime inventory follow-up

User confirmed only OpenAI hosted access is currently available. Read-only checks on 2026-10-10 found no Ollama/LM Studio/llama executable in Windows PATH or common application/model locations; no matching installed-app registry entry, process or listener on ports 11434/1234/8080. WSL inventory includes Ubuntu; a bounded shell check inside Ubuntu found neither ollama/llama-server on PATH nor common Ollama binaries/model manifests. No model service, Docker or download was started (the Ubuntu inspection shell started the distro). This is a bounded inventory, not proof against custom locations. Local evaluation currently lacks a discovered executable/model.

Claude/Grok credentials remain unavailable per user, with no permission inferred to use sibling-project keys. Continue dataset, scoring, OpenAI and native domain work independently. Model installation/download choice and a real manual timing session remain future unblock items.
