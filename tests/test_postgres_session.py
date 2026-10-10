from contextlib import contextmanager
from uuid import uuid4
import pytest
from backend.postgres_session import PostgresSession, PostgresSessionError


class Connection:
    def __init__(self, role=(False, False)):
        self.role = role
        self.autocommit = True
        self.calls = []
        self.closed = False
    @contextmanager
    def transaction(self):
        self.calls.append('begin')
        try:
            yield
        except Exception:
            self.calls.append('rollback')
            raise
        else:
            self.calls.append('commit')
    def execute(self, sql, params=()):
        self.calls.append((sql, params))
        return self
    def fetchone(self):
        return self.role
    def close(self):
        self.closed = True


def test_tenant_set_locally_before_body_and_connection_closed():
    conn = Connection(); tenant = str(uuid4())
    session = PostgresSession('test-only', connect=lambda _: conn)
    with session.transaction(tenant) as current:
        assert current is conn
        assert ("SELECT set_config('app.tenant_id', %s, true)", (tenant,)) in conn.calls
        assert 'commit' not in conn.calls
    assert conn.calls[-1] == 'commit' and conn.closed


def test_failure_rolls_back_without_retry():
    conn = Connection(); calls = []
    def factory(dsn):
        calls.append(dsn); return conn
    with pytest.raises(RuntimeError, match='business failure'):
        with PostgresSession('test-only', connect=factory).transaction(uuid4()):
            raise RuntimeError('business failure')
    assert calls == ['test-only'] and conn.calls[-1] == 'rollback' and conn.closed


@pytest.mark.parametrize('role', [(True, False), (False, True), None])
def test_privileged_runtime_roles_rejected_before_body(role):
    conn = Connection(role)
    with pytest.raises(PostgresSessionError, match='unsafe_runtime_role'):
        with PostgresSession('test-only', connect=lambda _: conn).transaction(uuid4()):
            pytest.fail('unsafe role reached business code')
    assert conn.closed and conn.calls[-1] == 'rollback'


def test_bad_tenant_never_opens_connection():
    def forbidden(_):
        pytest.fail('connection attempted before tenant validation')
    with pytest.raises(ValueError):
        with PostgresSession('test-only', connect=forbidden).transaction('unmapped-tenant'):
            pass


def test_implicit_transaction_connection_rejected():
    conn = Connection(); conn.autocommit = False
    with pytest.raises(PostgresSessionError, match='explicit_transactions'):
        with PostgresSession('test-only', connect=lambda _: conn).transaction(uuid4()):
            pytest.fail('implicit transaction accepted')
    assert conn.closed
