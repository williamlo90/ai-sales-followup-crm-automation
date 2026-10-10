from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4
import json
import pytest
from backend.postgres_store import translate, Cursor, PostgresStore, StorageError


def test_placeholder_identifier_mapping_never_rewrites_parameter_values():
    query, values = translate('INSERT INTO deals VALUES(?,?,?,?) ON CONFLICT(tenant,id) DO UPDATE SET payload=excluded.payload', ('tenant?', 'id', 1, '{"tenant":"?"}'))
    assert query == 'INSERT INTO deals(tenant_id,id,version,payload) VALUES(%s,%s,%s,%s) ON CONFLICT(tenant_id,id) DO UPDATE SET payload=excluded.payload'
    assert values == ('tenant?', 'id', 1, '{"tenant":"?"}')


def test_operations_explicit_idempotency_mapping():
    args = ('t','operation','proposal','crm','effect','hash','dispatched',None)
    query, values = translate('INSERT INTO operations(tenant,id,proposal_id,kind,effect_key,payload_hash,status,result) VALUES(?,?,?,?,?,?,?,?)',args)
    assert 'result,idempotency_key)' in query and values == (*args, 'operation')


def test_ingestion_boolean_mapping_and_unknown_insert_rejected():
    query, values = translate('INSERT INTO ingestion_messages VALUES(?,?,?,?,?,?,?,?,?)',tuple(range(9)))
    assert values[7] is True and values[6] == 6
    with pytest.raises(StorageError): translate('INSERT INTO surprise VALUES(?)',(1,))


def test_row_types_match_shared_domain_contract():
    ident = uuid4(); instant = datetime.now(timezone.utc)
    cursor = Cursor(SimpleNamespace(description=[SimpleNamespace(name=n) for n in ['tenant_id','payload','expires_at','id']]))
    row = cursor.normalize((ident, {'z':1,'a':'value'}, instant, ident))
    assert row['tenant'] == str(ident) and row[0] == str(ident)
    assert row['payload'] == '{"a":"value","z":1}'
    assert datetime.fromisoformat(row['expires_at']) == instant
    assert dict(row)['id'] == str(ident)


def test_actorless_postgres_transaction_denied():
    with pytest.raises(StorageError, match='actor_required'):
        with PostgresStore('unused').connect():
            pytest.fail('Unscoped connection opened')
