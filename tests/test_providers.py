import json
import httpx
import pytest
from backend.providers import ModelAdapter,ModelProfile,ProviderError

REVIEW={'status':'review','commitments':[],'missing_information':['exact date'],'conflicts':[]}


def envelope(provider,text):
    if provider=='openai':return {'status':'completed','output':[{'content':[{'type':'output_text','text':text}]}],'usage':{'input_tokens':12,'output_tokens':5}}
    if provider=='claude':return {'stop_reason':'end_turn','content':[{'type':'text','text':text}]}
    if provider=='grok':return {'choices':[{'finish_reason':'stop','message':{'content':text}}]}
    return {'done':True,'done_reason':'stop','message':{'content':text},'eval_count':5}


@pytest.mark.parametrize('provider',['openai','claude','grok','ollama'])
def test_provider_contracts_same_validated_output(provider):
    requests=[]
    def respond(request):
        body=json.loads(request.content);requests.append(body)
        assert body['model']=='test-model'
        assert 'tools' not in body
        return httpx.Response(200,json=envelope(provider,json.dumps(REVIEW)))
    adapter=ModelAdapter(ModelProfile(provider,'test-model',key='test-only',max_calls=1),transport=httpx.MockTransport(respond))
    result,trace=adapter.extract([{'text':'Maybe next week'}],{})
    assert result.status=='review'
    assert trace['validation']=='contract-double'
    assert trace['cost_usd'] is None
    assert 'test-only' not in json.dumps(trace)
    with pytest.raises(ProviderError,match='budget'):adapter.extract([],{})
    assert len(requests)==1


@pytest.mark.parametrize('provider',['openai','claude','grok','ollama'])
@pytest.mark.parametrize('text',['not json',json.dumps({**REVIEW,'approved':True}),json.dumps({**REVIEW,'status':'ready'})])
def test_malformed_or_authority_output_rejected(provider,text):
    adapter=ModelAdapter(ModelProfile(provider,'test-model',key='test-only',max_calls=1),
        transport=httpx.MockTransport(lambda r:httpx.Response(200,json=envelope(provider,text))))
    with pytest.raises(ProviderError,match='output_invalid'):adapter.extract([],{})


def test_local_only_no_hosted_fallback_and_no_cloud_alias():
    with pytest.raises(ProviderError,match='hosted_fallback_forbidden'):ModelAdapter(ModelProfile('openai','test',local_only=True))
    with pytest.raises(ProviderError,match='remote_model_forbidden'):ModelAdapter(ModelProfile('ollama','test-cloud',local_only=True))


@pytest.mark.parametrize('status,code',[(401,'credentials_rejected'),(429,'rate_limited'),(503,'unavailable'),(302,'unavailable')])
def test_provider_errors_do_not_retry_or_echo_body(status,code):
    calls=[]
    def respond(request):calls.append(1);return httpx.Response(status,text='secret error body')
    adapter=ModelAdapter(ModelProfile('openai','test',key='test',max_calls=2),transport=httpx.MockTransport(respond))
    with pytest.raises(ProviderError,match=code) as exc:adapter.extract([],{})
    assert 'secret' not in str(exc.value)
    assert len(calls)==1


def test_timeout_no_fallback():
    def respond(request):raise httpx.ReadTimeout('private context')
    adapter=ModelAdapter(ModelProfile('ollama','local-model',local_only=True,max_calls=1),transport=httpx.MockTransport(respond))
    with pytest.raises(ProviderError,match='transport_failure'):adapter.extract([],{})


def test_refusal_and_oversize_input():
    adapter=ModelAdapter(ModelProfile('openai','test',key='test',max_calls=2),transport=httpx.MockTransport(lambda r:
        httpx.Response(200,json={'status':'completed','output':[{'content':[{'type':'refusal'}]}]})))
    with pytest.raises(ProviderError,match='input_limit'):adapter.extract([{'text':'a'*64001}],{})
    assert adapter.calls==0
    with pytest.raises(ProviderError,match='refusal'):adapter.extract([],{})


def test_one_inflight_request_and_budget_not_consumed_by_busy_call():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    entered,release=Event(),Event()
    def respond(request):
        entered.set()
        assert release.wait(5)
        return httpx.Response(200,json=envelope('ollama',json.dumps(REVIEW)))
    adapter=ModelAdapter(ModelProfile('ollama','local-model',max_calls=3),transport=httpx.MockTransport(respond))
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(adapter.extract,[],{})
        assert entered.wait(5)
        try:
            with pytest.raises(ProviderError,match='model_busy'):adapter.extract([],{})
            assert adapter.calls==1
        finally:release.set()
        assert future.result()[0].status=='review'
