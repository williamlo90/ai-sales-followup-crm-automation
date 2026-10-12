"""Explicit Phase7 PostgreSQL migration/RLS probe in an isolated lab database.

Creates and removes only a uniquely named test schema and test role. No app
repository, connector or workflow acceptance is implied by these probes.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import traceback
from uuid import uuid4
import psycopg
from psycopg import sql
from backend.postgres_session import PostgresSession, PostgresSessionError
from scripts.migrations import apply


def probe(dsn, application=False, restart_container=None, graph=False, n8n=False, odoo=False):
    suffix = uuid4().hex
    schema = 'sales_probe_' + suffix
    role = 'sales_probe_' + suffix
    password = secrets.token_urlsafe(32)
    tenants = [uuid4(), uuid4()]
    passed = []
    with psycopg.connect(dsn, autocommit=True, connect_timeout=5) as owner:
        database, version = owner.execute('SELECT current_database(), version()').fetchone()
        if database != 'sales_phase7_acceptance':
            raise ValueError('Requires dedicated sales_phase7_acceptance database')
        created_schema = created_role = False
        try:
            owner.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
            created_schema = True
            owner.execute(sql.SQL('SET search_path TO {}').format(sql.Identifier(schema)))
            apply(owner); apply(owner)
            assert owner.execute('SELECT count(*) FROM migration_checksums').fetchone()[0] == 7
            passed.append('all_seven_migrations_and_replay')
            owner.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOBYPASSRLS').format(sql.Identifier(role), sql.Literal(password)))
            created_role = True
            owner.execute(sql.SQL('GRANT USAGE ON SCHEMA {} TO {}').format(sql.Identifier(schema), sql.Identifier(role)))
            owner.execute(sql.SQL('GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA {} TO {}').format(sql.Identifier(schema), sql.Identifier(role)))
            for tenant in tenants:
                owner.execute('INSERT INTO tenants VALUES(%s,%s)', (tenant, 'acceptance-only'))
                owner.execute('INSERT INTO deals VALUES(%s,%s,1,%s::jsonb)', (tenant, 'shared-id', '{}'))

            def connect(_):
                return psycopg.connect(dsn, user=role, password=password,
                    options=f'-c search_path={schema}', autocommit=True, connect_timeout=5)
            session = PostgresSession('injected-lab-connection', connect=connect)
            with connect(None) as unscoped:
                assert unscoped.execute('SELECT count(*) FROM deals').fetchone()[0] == 0
            passed.append('unscoped_runtime_sees_zero_rows')
            for tenant in tenants:
                with session.transaction(tenant) as conn:
                    rows = conn.execute('SELECT tenant_id,id FROM deals').fetchall()
                    assert rows == [(tenant, 'shared-id')]
            passed.append('tenant_read_isolation')
            try:
                with session.transaction(tenants[0]) as conn:
                    conn.execute('INSERT INTO deals VALUES(%s,%s,1,%s::jsonb)', (tenants[1], 'forbidden', '{}'))
            except psycopg.errors.InsufficientPrivilege:
                passed.append('cross_tenant_write_denied')
            else:
                raise AssertionError('Cross-tenant write was accepted')
            try:
                with session.transaction(tenants[0]) as conn:
                    conn.execute('INSERT INTO deals VALUES(%s,%s,1,%s::jsonb)', (tenants[0], 'rollback', '{}'))
                    raise RuntimeError('deliberate-rollback')
            except RuntimeError as exc:
                if str(exc) != 'deliberate-rollback': raise
            with session.transaction(tenants[0]) as conn:
                assert conn.execute("SELECT count(*) FROM deals WHERE id='rollback'").fetchone()[0] == 0
            passed.append('transaction_rollback_and_reconnect')
            if application:
                from psycopg.conninfo import make_conninfo
                from scripts.postgres_app_acceptance import check_application
                runtime_dsn = make_conninfo(dsn, user=role, password=password, options=f'-c search_path={schema}')
                passed.extend(check_application(owner, runtime_dsn, tenants, restart_container=restart_container))
                if owner.closed:
                    owner = psycopg.connect(dsn,autocommit=True,connect_timeout=5)
                    owner.execute(sql.SQL('SET search_path TO {}').format(sql.Identifier(schema)))
            if odoo:
                from psycopg.conninfo import make_conninfo
                from scripts.postgres_odoo_acceptance import check_odoo
                runtime_dsn = make_conninfo(dsn, user=role, password=password, options=f'-c search_path={schema}')
                passed.extend(check_odoo(owner, runtime_dsn, tenants[0]))
            if n8n:
                from psycopg.conninfo import make_conninfo
                from scripts.postgres_n8n_acceptance import check_n8n
                runtime_dsn = make_conninfo(dsn, user=role, password=password, options=f'-c search_path={schema}')
                passed.extend(check_n8n(owner, runtime_dsn, tenants[0]))
            if graph:
                from psycopg.conninfo import make_conninfo
                from scripts.postgres_graph_acceptance import check_graph
                runtime_dsn = make_conninfo(dsn, user=role, password=password, options=f'-c search_path={schema}')
                passed.extend(check_graph(owner, runtime_dsn, tenants[0]))
            owner.execute("UPDATE migration_checksums SET sha256=%s WHERE version='001_foundation'", ('0'*64,))
            try:
                apply(owner)
            except ValueError as exc:
                if 'checksum mismatch' not in str(exc): raise
                passed.append('migration_checksum_drift_denied')
            else:
                raise AssertionError('Checksum drift accepted')
            return {'scope':'Real PostgreSQL migrations and session/RLS; additional selected checks are listed explicitly',
                    'application_scope':'FastAPI/shared-core persistence, approval and concurrency' if application else 'not run',
                    'odoo_scope':'Real project-owned Odoo activity approval, write and read-back' if odoo else 'not run',
                    'n8n_scope':'Real n8n engine with shared domain HTTP/PostgreSQL' if n8n else 'not run',
                    'graph_scope': 'Real Graph delta and PostgreSQL; no remote writes' if graph else 'not run',
                    'server':version, 'checks':passed, 'passed':len(passed)}
        finally:
            # Names are generated in this function, never from user input. These
            # objects contain only the above disposable probes in the fixed lab DB.
            if owner.closed:
                owner = psycopg.connect(dsn,autocommit=True,connect_timeout=5)
            owner.execute('SET search_path TO public')
            if created_schema:
                owner.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))
            if created_role:
                owner.execute(sql.SQL('DROP ROLE {}').format(sql.Identifier(role)))
            owner.close()


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--application', action='store_true')
    parser.add_argument('--graph', action='store_true', help='Read the explicitly selected synthetic Graph mailbox')
    parser.add_argument('--n8n', action='store_true', help='Run isolated real n8n workflows against native HTTP/PostgreSQL')
    parser.add_argument('--odoo', action='store_true', help='Execute synthetic activity in explicitly configured project-owned Odoo lab')
    parser.add_argument('--restart-container', help='Exact owned256MiB acceptance container ID; requires --application')
    args = parser.parse_args()
    if args.restart_container and not args.application: raise SystemExit('Restart requires application probe')
    if os.environ.get('SALES_PHASE7_ACCEPTANCE') != 'enabled':
        raise SystemExit('Explicit SALES_PHASE7_ACCEPTANCE=enabled required')
    dsn = os.environ.get('SALES_POSTGRES_DSN')
    if not dsn: raise SystemExit('Project lab SALES_POSTGRES_DSN required')
    # Reserve output before touching the database; preserve failed runs as failed.
    with args.output.open('x') as out:
        try:
            result = probe(dsn, args.application, args.restart_container, args.graph, args.n8n, args.odoo)
        except Exception as exc:
            frames=traceback.extract_tb(exc.__traceback__)
            last=frames[-1]
            json.dump({'status':'failed','error_type':type(exc).__name__,
                       'location':Path(last.filename).name+':'+str(last.lineno)},out)
            raise SystemExit('PostgreSQL probe failed; output contains sanitized status') from None
        json.dump(result,out,indent=2)
    print(json.dumps({'passed':result['passed'],'scope':result['scope']}))


if __name__ == '__main__': main()
