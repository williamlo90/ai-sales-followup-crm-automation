import copy
import hashlib
import json
from datetime import datetime,timezone
from uuid import uuid4
import httpx
import pytest
from backend.domain import canonical
from backend.read_clients import OdooReadClient,ReadError
from backend.odoo_effects import OdooActivityAdapter


def fixture():
    tenant,actor,approver,proposal,approval,remote=[str(uuid4()) for _ in range(6)]
    operation={'id':str(uuid4()),'tenant':'local','proposal_id':str(uuid4()),'payload_hash':'a'*64,'kind':'crm'}
    payload={'deal_id':'d1','due_at':'2026-10-15T23:30:00-04:00','summary':'Send pricing'}
    preview={'kind':'activity','company_id':2,'opportunity_id':7,'assignee_id':8,'due_date':'2026-10-16',
             'summary':'Send pricing','source_version':'source-v1','contract_version':'1.0'}
    digest=hashlib.sha256(canonical(preview).encode()).hexdigest()
    binding={'local_payload_hash':operation['payload_hash'],'connector_tenant':tenant,'proposal_id':proposal,
             'approval_id':approval,'actor_id':actor,'preview':preview}
    workspace={'proposal':{'id':proposal,'tenant_id':tenant,'actor_id':actor,'kind':'activity','preview':copy.deepcopy(preview),
        'payload_hash':digest,'contract_version':'1.0','expires_at':'2026-10-20T00:00:00Z'},
        'approval':{'id':approval,'tenant_id':tenant,'proposal_id':proposal,'approver_id':approver,'payload_hash':digest,'expires_at':'2026-10-20T00:00:00Z'},'operation':None}
    remote_op={'id':remote,'tenant_id':tenant,'proposal_id':proposal,'approval_id':approval,'idempotency_key':operation['id'],
        'status':'verified','result':{'operation_id':remote,'payload_hash':digest,'record':{
            **{k:v for k,v in preview.items() if k not in {'source_version','contract_version'}},'external_id':99}}}
    state={'calls':[],'lose':False,'workspace':workspace,'remote':remote_op}
    def respond(request):
        state['calls'].append((request.method,request.url.path))
        if request.url.path=='/me':return httpx.Response(200,json={'id':actor,'tenant_id':tenant,'role':'operator'})
        if request.method=='POST':
            assert json.loads(request.content)=={'approval_id':approval,'idempotency_key':operation['id']}
            state['workspace']['operation']=copy.deepcopy(state['remote'])
            if state['lose']:raise httpx.ReadTimeout('private transport detail')
            return httpx.Response(200,json=state['remote'])
        if '/workspace/' in request.url.path:return httpx.Response(200,json=state['workspace'])
        return httpx.Response(200,json=state['remote'])
    client=OdooReadClient('http://127.0.0.1:8020',tenant,2,lambda:'fake',transport=httpx.MockTransport(respond))
    adapter=OdooActivityAdapter(client,lambda t,p:binding,{'d1':{'opportunity_id':7,'assignee_id':8}},write_enabled=True,
        clock=lambda:datetime(2026,10,9,tzinfo=timezone.utc))
    return adapter,operation,payload,binding,state


def test_success_maps_real_connector_receipt_fields():
    adapter,op,payload,_,state=fixture()
    receipt=adapter.dispatch(op,payload)
    assert receipt=={'operation_id':op['id'],'tenant_id':'local','payload_hash':op['payload_hash'],'external_id':'99','state':'read_back_verified'}
    assert adapter.observe(op)==receipt
    assert len([c for c in state['calls'] if c[0]=='POST'])==1


def test_lost_response_discovered_read_only_without_second_write():
    adapter,op,payload,_,state=fixture();state['lose']=True
    with pytest.raises(ReadError,match='write_outcome_unknown'):adapter.dispatch(op,payload)
    assert adapter.observe(op)['state']=='read_back_verified'
    assert len([c for c in state['calls'] if c[0]=='POST'])==1


def test_missing_operation_does_not_execute_on_reconcile():
    adapter,op,_,_,state=fixture()
    assert adapter.observe(op) is None
    assert all(method=='GET' for method,path in state['calls'])


@pytest.mark.parametrize('field,value', [('opportunity_id',100),('assignee_id',100),('due_date','2026-10-15'),('summary','other')])
def test_mapped_activity_mismatch_prevents_network(field,value):
    adapter,op,payload,binding,state=fixture();binding['preview'][field]=value
    with pytest.raises(ReadError,match='activity_preview_mismatch'):adapter.dispatch(op,payload)
    assert not state['calls']


@pytest.mark.parametrize('kind',['hash','tenant','self','expired','preview'])
def test_connector_approval_and_snapshot_mismatch_never_post(kind):
    adapter,op,payload,binding,state=fixture();ws=state['workspace']
    if kind=='hash':ws['approval']['payload_hash']='b'*64
    elif kind=='tenant':ws['approval']['tenant_id']=str(uuid4())
    elif kind=='self':ws['approval']['approver_id']=binding['actor_id']
    elif kind=='expired':ws['approval']['expires_at']='2020-01-01T00:00:00Z'
    else:ws['proposal']['preview']['source_version']='changed'
    with pytest.raises(ReadError):adapter.dispatch(op,payload)
    assert all(method=='GET' for method,path in state['calls'])


@pytest.mark.parametrize('kind',['record','idempotency','receipt_hash'])
def test_wrong_readback_does_not_claim_verified(kind):
    adapter,op,payload,_,state=fixture()
    if kind=='record':state['remote']['result']['record']['opportunity_id']=100
    elif kind=='idempotency':state['remote']['idempotency_key']=str(uuid4())
    else:state['remote']['result']['payload_hash']='b'*64
    with pytest.raises(ReadError):adapter.dispatch(op,payload)


def test_disabled_and_expired_observation():
    adapter,op,payload,_,state=fixture();adapter.write_enabled=False
    with pytest.raises(ReadError,match='write_disabled'):adapter.dispatch(op,payload)
    assert not state['calls']
    state['workspace']['operation']=state['remote']
    state['workspace']['approval']['expires_at']='2020-01-01T00:00:00Z'
    assert adapter.observe(op)['state']=='read_back_verified'


def test_unverified_remote_operation_stays_unknown_and_is_not_reexecuted():
    adapter,op,payload,_,state=fixture()
    state['remote']['status']='unknown';state['remote']['result']=None
    assert adapter.dispatch(op,payload) is None
    assert adapter.observe(op) is None
    assert adapter.dispatch(op,payload) is None
    assert len([c for c in state['calls'] if c[0]=='POST'])==1


def test_cross_connector_binding_and_oversize_summary_prevent_dispatch():
    adapter,op,payload,binding,state=fixture()
    binding['connector_tenant']='wrong'
    with pytest.raises(ReadError,match='binding_missing_or_stale'):adapter.dispatch(op,payload)
    assert not state['calls']
    adapter,op,payload,binding,state=fixture();payload['summary']='x'*121;binding['preview']['summary']=payload['summary']
    with pytest.raises(ReadError,match='activity_preview_mismatch'):adapter.dispatch(op,payload)
    assert not state['calls']
