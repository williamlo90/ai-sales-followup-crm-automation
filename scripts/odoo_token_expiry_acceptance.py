"""Actual server-side session expiry in the dedicated project04 connector lab."""
import argparse
import hashlib
import json
import os
import time
from pathlib import Path

import httpx
import psycopg
from psycopg.conninfo import make_conninfo
from backend.config import ROOT
from backend.read_clients import BoundedReader, ReadError


def run():
    if os.environ.get('SALES_PHASE7_ACCEPTANCE')!='enabled':raise ValueError('Lab switch required')
    path=Path(os.environ['SALES_ODOO_LAB_SESSION']).resolve()
    lab=(ROOT/'local/phase-7/sales04-odoo-20261010142205').resolve()
    if not path.is_relative_to(lab):raise ValueError('Exact project-owned lab session required')
    cfg=json.loads(path.read_text());compose=json.loads((lab/'compose.json').read_text())
    assert cfg['base_url']=='http://127.0.0.1:8024'
    dsn=make_conninfo(os.environ['SALES_POSTGRES_DSN'],dbname='odoo_ops_local')
    endpoint=cfg['base_url']+'/v1/opportunities'
    with psycopg.connect(dsn,autocommit=True) as conn, httpx.Client(base_url=cfg['base_url'],trust_env=False,timeout=20) as http:
        assert conn.execute('SELECT current_database()').fetchone()[0]=='odoo_ops_local'
        def counts():
            return {table:conn.execute('SELECT count(*) FROM '+table).fetchone()[0]
                    for table in ('proposals','approvals','operations')}
        before=counts()
        def login():
            response=http.post('/auth/login',json={'username':'operator.a',
                'password':compose['services']['manage']['environment']['DEMO_PASSWORD']})
            assert response.status_code==200
            return response.json()['access_token']
        token=login();digest=hashlib.sha256(token.encode()).hexdigest()
        reader=BoundedReader(lambda:token)
        reader.get(endpoint)
        changed=conn.execute("UPDATE sessions SET expires_at=now()+interval '2 seconds' WHERE token_hash=%s RETURNING actor_id",(digest,)).fetchall()
        assert len(changed)==1
        start=time.monotonic()
        while time.monotonic()-start<10:
            if conn.execute('SELECT expires_at<=now() FROM sessions WHERE token_hash=%s',(digest,)).fetchone()[0]:break
            time.sleep(.2)
        else:raise RuntimeError('Session did not expire')
        response=http.get('/v1/opportunities',headers={'Authorization':'Bearer '+token})
        assert response.status_code==401 and response.json()['error']=='invalid_session'
        try:reader.get(endpoint)
        except ReadError as error:assert error.code=='credentials_rejected'
        else:raise AssertionError('Expired token accepted by read adapter')
        BoundedReader(lambda:cfg['operator_token']).get(endpoint)
        fresh=login();BoundedReader(lambda:fresh).get(endpoint)
        assert counts()==before
        # Revoke only the new replacement test session; existing runner session stays valid.
        assert http.post('/auth/logout',headers={'Authorization':'Bearer '+fresh}).status_code==204
        return {'status':'passed','scope':'Actual expiry of a newly issued session on isolated Odoo connector',
                'valid_before_expiry':True,'http401_after_actual_database_expiry':True,
                'adapter_reports_credentials_rejected':True,'existing_session_still_valid':True,
                'fresh_login_restores_access':True,'business_row_counts_unchanged':True,
                'expiry_fixture_seconds':2,'elapsed_to_expiry_seconds':time.monotonic()-start,
                'limitations':['Only the new test session expiry was shortened in the isolated database',
                               'Connector token expiry, not Microsoft Graph token refresh',
                               'No business writes, model calls or email sends']}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists():raise SystemExit('Output exists')
    try:result=run()
    except Exception as error:result={'status':'failed','error_type':type(error).__name__}
    args.output.write_text(json.dumps(result,indent=2));print(json.dumps(result))
    raise SystemExit(0 if result['status']=='passed' else 1)
