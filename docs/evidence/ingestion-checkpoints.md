# Graph ingestion and checkpoints

Native implementation uses the shared source validation core within a single transaction for message changes, source revisions, audit and checkpoint. A generation comparison rejects pages fetched from stale checkpoints. Network reads happen outside the database transaction. A bounded poll processes at most ten pages and preserves continuation for the next invocation.

Message-to-deal mapping is explicit and supplied by trusted worker configuration. Unmapped/ambiguous messages block the whole page with `message_mapping_required`; nothing advances or disappears. Reassignment requires review. Source identity uses mailbox plus immutable message ID; a folder move cannot silently duplicate a source. Folder-to-folder transfer and deleted-source restoration are currently explicit review blockers, not automated features.

Repeated change keys do not inflate revisions. Contradictory content under one key and equal-time competing keys require review. Older modified timestamps do not regress current evidence. Removal tombstones are stored as higher source revisions, invalidate earlier proposal snapshots, and cannot be used as current evidence or model source text. This represents removal from the monitored collection; it does not assert global mailbox deletion.

Tests cover normal page polling, restart/replay, stale-generation rejection, rollback after a partially processed page or a failure before checkpoint commit, revisions, old updates, tombstones, restoration refusal, wrong worker/tenant, bounded continuation, cross-folder collision, deleted-evidence rejection and compatibility with older source payloads. Tests use temporary SQLite and an HTTP boundary double. PostgreSQL transaction/RLS and real Graph delta behavior remain Phase 7 acceptance; migration `004_ingestion.sql` is prepared only.

Validation commands: `.venv/Scripts/python.exe -m pytest -q`; `.venv/Scripts/python.exe -m scripts.migrations` (four-file plan only); `.venv/Scripts/python.exe -m scripts.export_skill_schemas`; `npm.cmd test --prefix mcp-server` (two native stdio suites). No external model, Graph, Odoo, container or send action was run. Scheduler/API activation, credentials, mapping review UI, and resynchronization/recovery commands remain pending.

Final validation on 2026-10-09 Asia/Jakarta: 145 Python tests passed; existing Starlette TestClient deprecation warning remains.
