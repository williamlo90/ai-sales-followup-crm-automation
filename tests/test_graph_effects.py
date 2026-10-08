import copy
import hashlib
import json
from uuid import uuid4
import httpx
import pytest
from backend.domain import canonical
from backend.graph_effects import GraphMailAdapter, PROPERTY, EffectRouter
from backend.read_clients import ReadError
from backend.execution import ExecutionService
from backend.models import ProposalInput, ApprovalInput


def fixture():
    payload={'recipient':'test@example.invalid','summary':'Follow-up','draft':'Please confirm pricing.'}
    op={'id':str(uuid4()),'tenant':'local','proposal_id':'proposal','kind':'email','payload_hash':hashlib.sha256(canonical(payload).encode()).hexdigest()}
    sent={'id':'immutable-message','isDraft':False,'subject':payload['summary'],'body':{'contentType':'text','content':payload['draft']},
          'toRecipients':[{'emailAddress':{'address':payload['recipient'],'name':'Test'}}],'ccRecipients':[],'bccRecipients':[],
          'sentDateTime':'2026-10-09T00:00:00Z','singleValueExtendedProperties':[{'id':PROPERTY,'value':op['id']}]}
    state={'calls':[],'items':[sent],'lose':False,'status':202,'request_id':str(uuid4())}
    def respond(request):
        state['calls'].append(request)
        assert request.url.host=='graph.microsoft.com'
        assert request.url.path.startswith('/v1.0/users/lab%40example.invalid/') or request.url.path.startswith('/v1.0/users/lab@example.invalid/')
        if request.method=='POST':
            body=json.loads(request.content)
            assert body['message']['body']['content']==payload['draft']
            assert body['message']['singleValueExtendedProperties'][0]['value']==op['id']
            assert 'saveToSentItems' not in body
            if state['lose']:raise httpx.ReadTimeout('secret transport details')
            return httpx.Response(state['status'],headers={'request-id':state['request_id']})
        assert PROPERTY in request.url.params['$filter'] and op['id'] in request.url.params['$filter']
        return httpx.Response(200,json={'value':state['items']})
    adapter=GraphMailAdapter('local','lab@example.invalid',lambda:'fake',lambda t,p:payload,
        recipients={payload['recipient']},send_enabled=True,transport=httpx.MockTransport(respond))
    return adapter,op,payload,state


def test_202_is_request_acceptance_then_sent_observation():
    adapter,op,payload,state=fixture()
    receipt=adapter.dispatch(op,payload)
    assert receipt['state']=='accepted' and receipt['external_id']=='graph-request:'+state['request_id']
    assert adapter.observe(op)['state']=='sent'
    assert len([r for r in state['calls'] if r.method=='POST'])==1


def test_timeout_can_only_observe_never_resend():
    adapter,op,payload,state=fixture();state['lose']=True
    with pytest.raises(ReadError,match='outcome_unknown'):adapter.dispatch(op,payload)
    assert adapter.observe(op)['external_id']=='immutable-message'
    assert len([r for r in state['calls'] if r.method=='POST'])==1


@pytest.mark.parametrize('count',[0,2])
def test_missing_or_duplicate_sent_matches_remain_unknown(count):
    adapter,op,_,state=fixture();state['items']=state['items']*count
    assert adapter.observe(op) is None
    assert all(r.method=='GET' for r in state['calls'])


@pytest.mark.parametrize('change',[
    {'subject':'Different'}, {'body':{'contentType':'text','content':'Altered'}}, {'isDraft':True},
    {'toRecipients':[{'emailAddress':{'address':'other@example.invalid'}}]},
    {'bccRecipients':[{'emailAddress':{'address':'hidden@example.invalid'}}]},
    {'singleValueExtendedProperties':[{'id':PROPERTY,'value':'wrong-operation'}]},
])
def test_unrelated_sent_item_cannot_confirm(change):
    adapter,op,_,state=fixture();state['items'][0].update(change)
    with pytest.raises(ReadError,match='observation_mismatch'):adapter.observe(op)


@pytest.mark.parametrize('status',[401,429,500,302])
def test_send_errors_never_retry(status):
    adapter,op,payload,state=fixture();state['status']=status
    with pytest.raises(ReadError,match='outcome_unknown'):adapter.dispatch(op,payload)
    assert len(state['calls'])==1


@pytest.mark.parametrize('setting',['disabled','allowlist','tenant','hash'])
def test_send_guards_before_network(setting):
    adapter,op,payload,state=fixture()
    if setting=='disabled':adapter.send_enabled=False
    elif setting=='allowlist':adapter.recipients=frozenset()
    elif setting=='tenant':op['tenant']='other'
    else:payload['draft']='Changed after approval'
    with pytest.raises(ReadError):adapter.dispatch(op,payload)
    assert not state['calls']


def test_router_does_not_fallback_to_other_effect():
    adapter,op,payload,state=fixture();router=EffectRouter(None,adapter)
    with pytest.raises(ReadError,match='adapter_unavailable'):router.dispatch({**op,'kind':'crm'},payload)
    assert not state['calls']


def test_shared_core_restart_reconciles_lost_send_without_second_post(lab,proposal):
    sales,actors,_=lab
    prepared=sales.prepare(actors['operator'],ProposalInput(**proposal))
    sales.approve(actors['approver'],prepared['id'],ApprovalInput(kind='email',payload_hash=prepared['payload_hash']))
    requests=[];sent=[]
    def respond(request):
        requests.append(request.method)
        if request.method=='POST':
            message=json.loads(request.content)['message']
            sent.append({**message,'id':'immutable-id','isDraft':False,'sentDateTime':'2026-10-09T00:00:00Z'})
            raise httpx.ReadTimeout('response lost after acceptance')
        return httpx.Response(200,json={'value':sent})
    adapter=GraphMailAdapter('lab','lab@example.invalid',lambda:'fake',lambda tenant,ident:prepared['payload'],
        send_enabled=True,recipients={'customer@example.test'},transport=httpx.MockTransport(respond))
    executor=ExecutionService(sales,adapter,enabled=True,send_enabled=True,recipients=frozenset({'customer@example.test'}))
    first=executor.execute(actors['operator'],prepared['id'],'email')
    assert first['status']=='unknown'
    restarted=ExecutionService(sales,adapter,enabled=True,send_enabled=True,recipients=frozenset({'customer@example.test'}))
    assert restarted.execute(actors['operator'],prepared['id'],'email')['id']==first['id']
    observed=restarted.reconcile(actors['operator'],first['id'])
    assert observed['status']=='accepted' # Sent Items is not delivered/read.
    assert requests==['POST','GET']
