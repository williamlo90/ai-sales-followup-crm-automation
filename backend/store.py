"""Durable SQLite local harness. PostgreSQL acceptance is explicitly separate."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS deals (
 tenant TEXT NOT NULL, id TEXT NOT NULL, version INTEGER NOT NULL,
 payload TEXT NOT NULL, PRIMARY KEY(tenant,id));
CREATE TABLE IF NOT EXISTS sources (
 tenant TEXT NOT NULL, id TEXT NOT NULL, revision INTEGER NOT NULL,
 deal_id TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(tenant,id),
 FOREIGN KEY(tenant,deal_id) REFERENCES deals(tenant,id));
CREATE TABLE IF NOT EXISTS proposals (
 tenant TEXT NOT NULL, id TEXT NOT NULL, deal_id TEXT NOT NULL,
 actor_id TEXT NOT NULL, payload TEXT NOT NULL, payload_hash TEXT NOT NULL,
 created_at TEXT NOT NULL, expires_at TEXT NOT NULL, version INTEGER NOT NULL,
 PRIMARY KEY(tenant,id), UNIQUE(tenant,deal_id,version),
 FOREIGN KEY(tenant,deal_id) REFERENCES deals(tenant,id));
CREATE TABLE IF NOT EXISTS approvals (
 tenant TEXT NOT NULL, proposal_id TEXT NOT NULL, kind TEXT NOT NULL,
 actor_id TEXT NOT NULL, payload_hash TEXT NOT NULL,
 created_at TEXT NOT NULL, PRIMARY KEY(tenant,proposal_id,kind),
 FOREIGN KEY(tenant,proposal_id) REFERENCES proposals(tenant,id));
CREATE TABLE IF NOT EXISTS audit_events (
 id INTEGER PRIMARY KEY AUTOINCREMENT, tenant TEXT NOT NULL,
 actor_id TEXT NOT NULL, action TEXT NOT NULL, resource_id TEXT NOT NULL,
 at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS operations (
 tenant TEXT NOT NULL, id TEXT NOT NULL, proposal_id TEXT NOT NULL,
 kind TEXT NOT NULL CHECK(kind IN ('crm','email')), effect_key TEXT NOT NULL,
 payload_hash TEXT NOT NULL, status TEXT NOT NULL, result TEXT,
 PRIMARY KEY(tenant,id), UNIQUE(tenant,effect_key),
 FOREIGN KEY(tenant,proposal_id,kind) REFERENCES approvals(tenant,proposal_id,kind));
CREATE TABLE IF NOT EXISTS commitments (
 tenant TEXT NOT NULL, deal_id TEXT NOT NULL, id TEXT NOT NULL,
 revision INTEGER NOT NULL, payload TEXT NOT NULL,
 PRIMARY KEY(tenant,deal_id,id,revision),
 FOREIGN KEY(tenant,deal_id) REFERENCES deals(tenant,id));
CREATE TABLE IF NOT EXISTS model_runs (
 tenant TEXT NOT NULL, id TEXT NOT NULL, actor_id TEXT NOT NULL,
 deal_id TEXT NOT NULL, metadata TEXT NOT NULL, PRIMARY KEY(tenant,id),
 FOREIGN KEY(tenant,deal_id) REFERENCES deals(tenant,id));
CREATE TABLE IF NOT EXISTS ingestion_streams (
 tenant TEXT NOT NULL, stream TEXT NOT NULL, generation INTEGER NOT NULL,
 checkpoint TEXT, PRIMARY KEY(tenant,stream));
CREATE TABLE IF NOT EXISTS ingestion_messages (
 tenant TEXT NOT NULL, stream TEXT NOT NULL, external_id TEXT NOT NULL,
 source_id TEXT NOT NULL, deal_id TEXT NOT NULL, change_key TEXT,
 modified_at TEXT, deleted INTEGER NOT NULL, content_hash TEXT NOT NULL,
 PRIMARY KEY(tenant,stream,external_id),
 FOREIGN KEY(tenant,source_id) REFERENCES sources(tenant,id));
CREATE TABLE IF NOT EXISTS connector_bindings (
 tenant TEXT NOT NULL, proposal_id TEXT NOT NULL, connector_tenant TEXT NOT NULL,
 connector_proposal TEXT NOT NULL, payload TEXT NOT NULL,
 PRIMARY KEY(tenant,proposal_id), UNIQUE(connector_tenant,connector_proposal),
 FOREIGN KEY(tenant,proposal_id) REFERENCES proposals(tenant,id));
CREATE TABLE IF NOT EXISTS workflow_jobs (
 tenant TEXT NOT NULL, id TEXT NOT NULL, worker_id TEXT NOT NULL, deal_id TEXT NOT NULL,
 journey TEXT NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL, proposal_id TEXT,
 operation_id TEXT, next_at TEXT NOT NULL, lease_id TEXT, lease_until TEXT,
 error_code TEXT, PRIMARY KEY(tenant,id), FOREIGN KEY(tenant,deal_id) REFERENCES deals(tenant,id));
"""


class Store:
    def __init__(self, path: str | Path):
        self.path = str(path)
        if self.path == ":memory:":
            raise ValueError("Use a temporary file for isolated durable harness tests")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(SCHEMA)

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
