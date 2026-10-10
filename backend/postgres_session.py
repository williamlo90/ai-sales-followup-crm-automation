"""Tenant-scoped PostgreSQL transactions; repository composition is separate.

The connection factory is injected for contract tests. Runtime connections use
psycopg, never provision schemas/roles, and never retry a possibly committed write.
"""
from contextlib import contextmanager
from uuid import UUID


class PostgresSessionError(Exception):
    pass


def connect_runtime(dsn):
    try:
        import psycopg
        return psycopg.connect(dsn, autocommit=True, connect_timeout=5)
    except Exception:
        raise PostgresSessionError('postgres_connection_unavailable') from None


class PostgresSession:
    def __init__(self, dsn, *, connect=connect_runtime):
        if not isinstance(dsn, str) or not dsn.strip():
            raise ValueError('PostgreSQL DSN required')
        self._dsn = dsn
        self._connect = connect

    @contextmanager
    def transaction(self, tenant_id):
        # Trusted authenticated tenant mapping must supply an explicit UUID.
        # Never derive this value from SQL, model output or an unscoped default.
        tenant = str(UUID(str(tenant_id)))
        connection = self._connect(self._dsn)
        try:
            if not connection.autocommit:
                raise PostgresSessionError('postgres_requires_explicit_transactions')
            with connection.transaction():
                role = connection.execute(
                    'SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname=current_user'
                ).fetchone()
                if role is None or role[0] or role[1]:
                    raise PostgresSessionError('postgres_unsafe_runtime_role')
                connection.execute("SELECT set_config('app.tenant_id', %s, true)", (tenant,))
                connection.execute("SELECT set_config('statement_timeout', '5000', true)")
                connection.execute("SELECT set_config('lock_timeout', '2000', true)")
                connection.execute("SELECT set_config('idle_in_transaction_session_timeout', '10000', true)")
                yield connection
        finally:
            connection.close()
