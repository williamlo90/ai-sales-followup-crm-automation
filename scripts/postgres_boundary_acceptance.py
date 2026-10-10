"""Real PostgreSQL ingestion/ledger tests with explicitly simulated remote edges."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Lock
import httpx
from backend.domain import SalesService, DomainError
from backend.models import Actor, ProposalInput, ApprovalInput
from backend.postgres_store import PostgresStore
from backend.ingestion import GraphIngestion
from backend.read_clients import GraphReadClient
from backend.execution import ExecutionService


def check_boundaries(dsn, records):
    actors = {k:Actor.model_validate(v) for k,v in records.items()}
    service = SalesService(PostgresStore(dsn)); worker = actors['worker']
    now = datetime.now(timezone.utc)
    item = {'id':'boundary-message','changeKey':'1','receivedDateTime':now.isoformat(),
            'lastModifiedDateTime':now.isoformat(),'body':{'contentType':'text','content':'Morgan will provide the signed checklist.'}}
    graph = GraphReadClient(worker.tenant_id,'sandbox@example.test',lambda:'double-only',transport=httpx.MockTransport(
        lambda request:httpx.Response(200,json={'value':[item],'@odata.deltaLink':'https://graph.microsoft.com'+graph.path+'?$deltatoken=test'})))
    ingest = GraphIngestion(service,worker,graph,{'boundary-message':'app-deal'})
    bad_page = {'items':[item,{**item,'id':'unmapped'}],'complete':True,
        'checkpoint':{'tenant_id':worker.tenant_id,'mailbox_id':graph.mailbox_id,'url':'https://graph.microsoft.com'+graph.path+'?$deltatoken=test'}}
    try:ingest.commit(0,bad_page)
    except DomainError as exc:assert exc.code=='message_mapping_required'
    else:raise AssertionError('Invalid page accepted')
    assert ingest.state()==(0,None)
    with service.store.connect(worker) as conn:
        assert conn.execute('SELECT count(*) FROM ingestion_messages WHERE tenant=?',(worker.tenant_id,)).fetchone()[0]==0
    assert ingest.poll()['changed']==1
    restarted = GraphIngestion(SalesService(PostgresStore(dsn)),worker,graph,{'boundary-message':'app-deal'})
    assert restarted.poll()['changed']==0 and restarted.state()[0]==2
    source = next(s for s in service.context(actors['operator'],'app-deal')['sources'] if s['external_id'].startswith('graph:'))
    assert source['revision']==1
    proposal = service.prepare(actors['operator'],ProposalInput(deal_id='app-deal',deal_version=1,
        summary='Signed checklist',draft='Please confirm the signed checklist.',due_at=now+timedelta(days=1),
        evidence=[{'source_id':source['external_id'],'revision':1,'quote':item['body']['content']}]))
    service.approve(actors['approver'],proposal['id'],ApprovalInput(kind='crm',payload_hash=proposal['payload_hash']))

    class LostResponseDouble:
        def __init__(self):self.calls=0;self.receipts={};self.lock=Lock()
        def dispatch(self,operation,payload):
            with self.lock:
                self.calls+=1
                self.receipts[operation['id']]={'operation_id':operation['id'],'tenant_id':operation['tenant'],
                    'payload_hash':operation['payload_hash'],'external_id':'simulated-only','state':'read_back_verified'}
            raise TimeoutError('Simulated lost response; no external request')
        def observe(self,operation):return self.receipts[operation['id']]
    remote = LostResponseDouble(); execution = ExecutionService(service,remote,enabled=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        operations = list(pool.map(lambda _:execution.execute(actors['operator'],proposal['id'],'crm'),range(8)))
    assert len({r['id'] for r in operations})==1 and remote.calls==1
    operation_id = operations[0]['id']
    assert service.operation(actors['auditor'],operation_id)['status']=='unknown'
    recovered = ExecutionService(SalesService(PostgresStore(dsn)),remote,enabled=True)
    assert recovered.reconcile(actors['operator'],operation_id)['status']=='verified'
    assert recovered.execute(actors['operator'],proposal['id'],'crm')['id']==operation_id and remote.calls==1
    with service.store.connect(worker) as conn:
        assert conn.execute('SELECT count(*) FROM operations WHERE tenant=?',(worker.tenant_id,)).fetchone()[0]==1
    return ['postgres_ingestion_invalid_page_atomic_rollback_mock_graph',
            'postgres_ingestion_checkpoint_reconnect_and_replay_mock_graph',
            'postgres_concurrent_execution_one_ledger_and_one_simulated_dispatch',
            'postgres_unknown_reconciliation_no_redispatch_simulated_remote']
