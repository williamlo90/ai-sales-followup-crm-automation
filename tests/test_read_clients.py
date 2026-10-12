import httpx
import pytest
from backend.read_clients import GraphReadClient, OdooReadClient, BoundedReader, ReadError


def graph(respond):
    return GraphReadClient('tenant','test@example.invalid',lambda:'fake-token',transport=httpx.MockTransport(respond),sleep=lambda _:None)


def test_graph_pagination_checkpoint_and_tombstones():
    calls=[]
    def respond(request):
        calls.append(str(request.url))
        assert request.headers['Authorization']=='Bearer fake-token'
        assert 'ImmutableId' in request.headers['Prefer']
        if len(calls)==1:return httpx.Response(200,json={'value':[{'id':'m1'}],'@odata.nextLink':base+'?$skiptoken=opaque'})
        return httpx.Response(200,json={'value':[{'id':'m1','@removed':{'reason':'deleted'}}],'@odata.deltaLink':base+'?$deltatoken=opaque'})
    client=graph(respond);base='https://graph.microsoft.com'+client.path
    first=client.page();assert first['complete'] is False
    second=client.page(first['checkpoint'])
    assert second['complete'] and '@removed' in second['items'][0]
    assert len(calls)==2 and '$skiptoken=opaque' in calls[1]


@pytest.mark.parametrize('url',[
    'https://evil.example/token','https://graph.microsoft.com.evil.example/v1.0/users/test/messages/delta',
    'https://graph.microsoft.com/v1.0/users/other/mailFolders/inbox/messages/delta',
    'http://graph.microsoft.com/v1.0/users/test/messages/delta','https://graph.microsoft.com@evil.example/',
])
def test_graph_untrusted_pagination_never_receives_token(url):
    calls=[]
    client=graph(lambda r:calls.append(r))
    with pytest.raises(ReadError,match='checkpoint_scope_mismatch'):
        client.page({'tenant_id':'tenant','mailbox_id':'test@example.invalid','url':url})
    assert not calls


def test_graph_wrong_tenant_and_response_scope():
    client=graph(lambda r:httpx.Response(200,json={'value':[],'@odata.nextLink':'https://evil.example'}))
    with pytest.raises(ReadError,match='scope_mismatch'):client.page({'tenant_id':'other','mailbox_id':'test@example.invalid','url':client.initial})
    with pytest.raises(ReadError,match='scope_mismatch'):client.page()


def test_graph_actual_odata_folder_checkpoint_and_scope():
    client=graph(lambda r: None)
    url="https://graph.microsoft.com/v1.0/users/test@example.invalid/mailFolders('inbox')/messages/delta?$deltatoken=opaque"
    assert client.validate_link(url)==url
    for bad in (url.replace("'inbox'", "'archive'"),
                url.replace('test@example.invalid','other@example.invalid'),
                url.replace('graph.microsoft.com','evil.invalid')):
        with pytest.raises(ReadError,match='checkpoint_scope_mismatch'):
            client.validate_link(bad)


def test_graph_expired_delta_and_cursor_cycle():
    with pytest.raises(ReadError,match='checkpoint_expired'):
        graph(lambda r:httpx.Response(400,json={'error':{'code':'syncStateNotFound','message':'private'}})).page()
    with pytest.raises(ReadError,match='pagination_cycle'):
        graph(lambda r:httpx.Response(200,json={'value':[],'@odata.nextLink':str(r.url)})).page()


@pytest.mark.parametrize('status,code',[(401,'credentials_rejected'),(403,'credentials_rejected'),(410,'checkpoint_expired'),(302,'read_rejected')])
def test_read_errors_sanitized_no_retry(status,code):
    calls=[]
    def respond(r):calls.append(r);return httpx.Response(status,text='secret-token')
    with pytest.raises(ReadError,match=code) as exc:graph(respond).page()
    assert len(calls)==1 and 'secret-token' not in str(exc.value)


def test_retry_after_is_bounded_and_respected():
    calls=[];waits=[]
    def respond(r):
        calls.append(r)
        return httpx.Response(429,headers={'Retry-After':'2'}) if len(calls)<3 else httpx.Response(200,json={'ok':True})
    reader=BoundedReader(lambda:'fake',transport=httpx.MockTransport(respond),sleep=waits.append)
    assert reader.get('https://graph.microsoft.com/test')=={'ok':True}
    assert waits==[2,2] and len(calls)==3
    reader=BoundedReader(lambda:'fake',transport=httpx.MockTransport(lambda r:httpx.Response(429,headers={'Retry-After':'3600'})),sleep=waits.append)
    with pytest.raises(ReadError,match='retry_later') as exc:reader.get('https://graph.microsoft.com/test')
    assert exc.value.retry_after==3600 and waits==[2,2]


def test_retry_exhaustion_and_response_limit():
    calls=[]
    def respond(r):calls.append(r);return httpx.Response(503)
    with pytest.raises(ReadError,match='retry_later'):graph(respond).page()
    assert len(calls)==3
    with pytest.raises(ReadError,match='response_limit'):graph(lambda r:httpx.Response(200,content=b'x'*1_048_577)).page()


def odoo(respond):
    return OdooReadClient('http://127.0.0.1:8020','tenant',2,lambda:'fake',transport=httpx.MockTransport(respond))


RECORD={'id':7,'company_id':2,'source':'odoo:crm.lead','version':'v1','name':'Synthetic','customer_id':4,'owner_id':3,'stage':'New'}


def test_odoo_reuses_connector_contract_without_writes():
    calls=[]
    def respond(r):
        calls.append(r);assert r.method=='GET'
        if r.url.path=='/me':return httpx.Response(200,json={'tenant_id':'tenant','role':'operator'})
        return httpx.Response(200,json={'items':[RECORD]} if r.url.path.endswith('opportunities') else RECORD)
    client=odoo(respond)
    assert client.opportunities()==[RECORD]
    assert client.opportunity(7)==RECORD
    assert [r.url.path for r in calls]==['/me','/v1/opportunities','/me','/v1/opportunities/7']


@pytest.mark.parametrize('bad',[{'items':[dict(RECORD,company_id=3)]},{'items':[RECORD],'next_cursor':'unsupported'},{'items':[RECORD,RECORD]}])
def test_odoo_rejects_wrong_company_or_unimplemented_pagination(bad):
    client=odoo(lambda r:httpx.Response(200,json={'tenant_id':'tenant','role':'auditor'} if r.url.path=='/me' else bad))
    with pytest.raises(ReadError):client.opportunities()


def test_odoo_wrong_tenant_stops_before_records():
    calls=[]
    def respond(r):calls.append(r);return httpx.Response(200,json={'tenant_id':'other','role':'operator'})
    with pytest.raises(ReadError,match='scope_mismatch'):odoo(respond).opportunities()
    assert len(calls)==1
