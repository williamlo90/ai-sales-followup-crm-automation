"""One authorized synthetic send; retain PostgreSQL ledger and never auto-resend."""
import argparse
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
from backend.config import ROOT
from backend.connector_runtime import token_reader
from backend.domain import SalesService, DomainError
from backend.models import Actor, DealInput, SourceInput, ProposalInput, ApprovalInput
from backend.postgres_store import PostgresStore
from backend.graph_effects import GraphMailAdapter
from backend.execution import ExecutionService
from scripts.migrations import apply


def run(dsn):
    folder=(ROOT/os.environ.get('SALES_GRAPH_SEND_SESSION','local/graph-ingestion')).resolve()
    if not folder.is_relative_to((ROOT/'local').resolve()):
        raise ValueError('Send session must stay inside project local directory')
    permit=json.loads((folder/'send-authorization.json').read_text())
    if permit.get('maximum_sends')!=1 or permit.get('sent') is not False:
        raise ValueError('One-send authorization required')
    if (folder/'send-attempt.json').exists():
        raise ValueError('Attempt already reserved; reconciliation only, never rerun send')
    cfg=json.loads((ROOT/'local/connectors.json').read_text())['graph']
    # Ensure token is present before provisioning or reserving a send.
    token=token_reader(cfg['token_file']);token()
    schema='sales_mail_'+uuid4().hex;role=schema;password=secrets.token_urlsafe(32)
    tenant=str(uuid4());actors={}
    with psycopg.connect(dsn,autocommit=True,connect_timeout=5) as owner:
        if owner.execute('SELECT current_database()').fetchone()[0]!='sales_phase7_acceptance':
            raise ValueError('Dedicated lab database required')
        owner.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
        owner.execute(sql.SQL('SET search_path TO {}').format(sql.Identifier(schema)))
        apply(owner)
        owner.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOBYPASSRLS').format(sql.Identifier(role),sql.Literal(password)))
        owner.execute(sql.SQL('GRANT USAGE ON SCHEMA {} TO {}').format(sql.Identifier(schema),sql.Identifier(role)))
        owner.execute(sql.SQL('GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA {} TO {}').format(sql.Identifier(schema),sql.Identifier(role)))
        owner.execute('INSERT INTO tenants VALUES(%s,%s)',(tenant,'one-send-synthetic-lab'))
        for name in ('worker','operator','approver'):
            actors[name]=Actor(id=str(uuid4()),tenant_id=tenant,role=name,deal_ids={'mail-test'})
            owner.execute('INSERT INTO actors(tenant_id,id,role) VALUES(%s,%s,%s)',(tenant,actors[name].id,name))
    runtime=make_conninfo(dsn,user=role,password=password,options=f'-c search_path={schema}')
    sales=SalesService(PostgresStore(runtime));now=datetime.now(timezone.utc)
    sales.put_deal(actors['worker'],'mail-test',DealInput(account_id='self-test',title='Authorized one-email test',recipient=permit['recipient'],version=1))
    text='Ini satu email percobaan proyek AI Sales Follow-up. Tidak perlu membalas.'
    sales.put_source(actors['worker'],'mail-test',SourceInput(external_id='user-send-authorization',revision=1,occurred_at=now,text=text))
    proposal=sales.prepare(actors['operator'],ProposalInput(deal_id='mail-test',deal_version=1,
        evidence=[{'source_id':'user-send-authorization','revision':1,'quote':text}],
        summary='[SALES-P04] Email percobaan '+uuid4().hex[:8],draft=text,due_at=now-timedelta(seconds=1)))
    payload=proposal['payload']
    adapter=GraphMailAdapter(tenant,cfg['mailbox'],token,lambda t,p:payload,
        recipients=frozenset({permit['recipient']}),send_enabled=True)
    execute=ExecutionService(sales,adapter,enabled=True,send_enabled=True,recipients=frozenset({permit['recipient']}))
    try:execute.execute(actors['operator'],proposal['id'],'email')
    except DomainError as error:assert error.code=='approval_required'
    else:raise AssertionError('Unapproved send accepted')
    sales.approve(actors['approver'],proposal['id'],ApprovalInput(kind='email',payload_hash=proposal['payload_hash']))
    # Keep reconcilable state even if the process/network fails after reservation.
    state={'runtime_dsn':runtime,'actor':actors['operator'].model_dump(mode='json'),
           'proposal_id':proposal['id'],'payload':payload,'mailbox':cfg['mailbox'],'token_file':cfg['token_file']}
    with (folder/'send-state.json').open('x',encoding='utf-8') as out:json.dump(state,out)
    with (folder/'send-attempt.json').open('x',encoding='utf-8') as out:
        json.dump({'reserved_at':now.isoformat(),'proposal_id':proposal['id'],'maximum_attempts':1},out)
    operation=execute.execute(actors['operator'],proposal['id'],'email')
    with (folder/'send-operation.json').open('x',encoding='utf-8') as out:json.dump(operation,out)
    permit['sent']=operation['status']=='accepted'
    permit['attempt_reserved']=True
    (folder/'send-authorization.json').write_text(json.dumps(permit,indent=2))
    # A second core request must return the existing ledger without dispatch.
    repeat=execute.execute(actors['operator'],proposal['id'],'email')
    assert repeat['id']==operation['id']
    observed=None
    try:observed=adapter.observe(operation)
    except Exception:pass  # Receipt persisted; no retry of the send on observation failure.
    return {'status':operation['status'],'send_attempts':1,'repeat_core_same_operation':True,
            'sent_items_verified':bool(observed and observed['state']=='sent'),
            'received_verified':False,'storage':'real PostgreSQL; schema and ledger retained',
            'approval':'user-authorized send, separate automated lab-role email approval',
            'scope':'one synthetic allowlisted email; accepted is not delivery proof'}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
    if os.environ.get('SALES_GRAPH_SEND_ACCEPTANCE')!='enabled':raise SystemExit('Explicit send acceptance switch required')
    try:result=run(os.environ['SALES_POSTGRES_DSN'])
    except Exception as error:result={'status':'stopped','error_type':type(error).__name__,'action':'inspect private ledger; never resend automatically'}
    with open(args.output,'x',encoding='utf-8') as out:json.dump(result,out,indent=2)
    print(json.dumps(result))
    return 0 if result['status']=='accepted' else 1


if __name__=='__main__':raise SystemExit(main())
