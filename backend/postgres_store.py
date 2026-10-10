"""PostgreSQL storage mapping for the shared domain's SQL contract.

Only identifier/placeholder/type differences are mapped here. Sales decisions
remain in the same domain services. Transactions serialize per tenant, matching
the harness's read-before-write semantics without serializing unrelated tenants.
"""
from contextlib import contextmanager
from datetime import datetime
import hashlib
import json
import re
from uuid import UUID
from backend.postgres_session import PostgresSession, PostgresSessionError


class StorageError(Exception):
    pass


class StorageIntegrityError(StorageError):
    pass


COLUMNS = {
    'deals':'tenant_id,id,version,payload',
    'sources':'tenant_id,id,revision,deal_id,payload',
    'proposals':'tenant_id,id,deal_id,actor_id,payload,payload_hash,created_at,expires_at,version',
    'approvals':'tenant_id,proposal_id,kind,actor_id,payload_hash,created_at',
    'commitments':'tenant_id,deal_id,id,revision,payload',
    'model_runs':'tenant_id,id,actor_id,deal_id,metadata',
    'ingestion_streams':'tenant_id,stream,generation,checkpoint',
    'ingestion_messages':'tenant_id,stream,external_id,source_id,deal_id,change_key,modified_at,deleted,content_hash',
    'connector_bindings':'tenant_id,proposal_id,connector_tenant,connector_proposal,payload',
    'workflow_jobs':'tenant_id,id,worker_id,deal_id,journey,payload,status,proposal_id,operation_id,next_at,lease_id,lease_until,error_code',
    'workflow_scans':'tenant_id,worker_id,kind,cursor',
}


def translate(statement, params):
    statement = re.sub(r'\btenant\b', 'tenant_id', statement)
    match = re.match(r'INSERT INTO (\w+) VALUES', statement, re.I)
    if match:
        table = match[1]
        if table not in COLUMNS: raise StorageError('unmapped_postgres_insert')
        statement = statement.replace(f'INTO {table} VALUES', f'INTO {table}({COLUMNS[table]}) VALUES', 1)
        if table == 'ingestion_messages':
            params = tuple(bool(v) if i == 7 else v for i,v in enumerate(params))
    if statement.startswith('INSERT INTO operations('):
        statement = statement.replace('status,result)', 'status,result,idempotency_key)').replace('VALUES(?,?,?,?,?,?,?,?)','VALUES(?,?,?,?,?,?,?,?,?)')
        params = (*params, params[1])
    return statement.replace('?', '%s'), params


class Row(dict):
    def __getitem__(self, key):
        return list(self.values())[key] if isinstance(key, int) else super().__getitem__(key)


class Cursor:
    def __init__(self, cursor): self.cursor = cursor
    def normalize(self, values):
        if values is None: return None
        row = Row()
        for column,value in zip(self.cursor.description, values):
            key = 'tenant' if column.name == 'tenant_id' else column.name
            if isinstance(value, (dict,list)):
                value = json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False)
            elif isinstance(value, UUID): value = str(value)
            elif isinstance(value, datetime): value = value.isoformat()
            row[key] = value
        if 'idempotency_key' in row:
            for key in ('idempotency_key','error_code','created_at'): row.pop(key,None)
        return row
    def fetchone(self): return self.normalize(self.cursor.fetchone())
    def fetchall(self): return [self.normalize(row) for row in self.cursor.fetchall()]
    def __iter__(self):
        for row in self.cursor: yield self.normalize(row)
    @property
    def rowcount(self): return self.cursor.rowcount


class Connection:
    def __init__(self, connection): self.connection = connection
    def execute(self, statement, params=()):
        import psycopg
        query,values = translate(statement,params)
        try:
            return Cursor(self.connection.execute(query,values))
        except psycopg.IntegrityError:
            raise StorageIntegrityError('postgres_integrity_error') from None
        except psycopg.Error:
            raise StorageError('postgres_statement_failed') from None


class PostgresStore:
    storage_name = 'postgresql'
    def __init__(self, dsn, *, session=None):
        self.session = session or PostgresSession(dsn)
    @contextmanager
    def connect(self, actor=None):
        if actor is None: raise StorageError('postgres_actor_required')
        from backend.domain import DomainError
        import psycopg
        try:
            tenant = str(UUID(actor.tenant_id)); ident = str(UUID(actor.id))
        except ValueError:
            raise DomainError('postgres_identity_mapping_required',403) from None
        try:
            with self.session.transaction(tenant) as conn:
                lock = int.from_bytes(hashlib.sha256(tenant.encode()).digest()[:8], 'big', signed=True)
                conn.execute('SELECT pg_advisory_xact_lock(%s)', (lock,))
                current = conn.execute('SELECT role,active FROM actors WHERE tenant_id=%s AND id=%s',(tenant,ident)).fetchone()
                if not current or not current[1] or current[0] != actor.role:
                    raise DomainError('database_identity_rejected',403)
                yield Connection(conn)
        except (psycopg.Error, PostgresSessionError):
            raise StorageError('postgres_transaction_unavailable') from None
    def ready(self):
        # A readiness call must not read tenant data with an unscoped identity.
        import psycopg
        try:
            with self.session.transaction(str(UUID(int=0))) as conn:
                if conn.execute("SELECT count(*) FROM migration_checksums").fetchone()[0] != 7:
                    raise StorageError('postgres_migrations_incomplete')
        except (psycopg.Error, PostgresSessionError):
            raise StorageError('postgres_unavailable') from None
