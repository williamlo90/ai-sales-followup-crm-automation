import json
import httpx
import pytest
from scripts import model_canary as canary
from backend.domain import DomainError
from backend.providers import ModelAdapter, ModelProfile
from test_providers import envelope


def test_canary_rejects_plausible_but_wrong_owner(tmp_path):
    result={'status':'ready','commitments':[{
        'id':'c1','revision':1,'supersedes':None,'owner':'Bob','description':'Send pricing proposal',
        'due_at':'2026-10-15T10:00:00Z','observed_at':'2026-10-09T00:00:00Z','state':'active',
        'evidence':{'source_id':'synthetic-message','revision':1,'quote':canary.SOURCE}}],
        'missing_information':[],'conflicts':[]}
    adapter=ModelAdapter(ModelProfile('openai','test-model',key='fake',max_calls=1),
        transport=httpx.MockTransport(lambda request:httpx.Response(200,json=envelope('openai',json.dumps(result)))))
    with pytest.raises(DomainError,match='canary_semantics_mismatch'):canary.exercise(adapter,tmp_path)
    assert adapter.calls==1


def test_canary_reservation_blocks_second_run_even_after_failure(tmp_path,monkeypatch,capsys):
    monkeypatch.setattr(canary,'ROOT',tmp_path)
    monkeypatch.setattr('sys.argv',['canary','--run'])
    monkeypatch.setattr(canary,'read_config',lambda:{'OPENAI_API_KEY':'test-secret','SALES_MODEL_CALL_LIMIT':'1'})
    calls=[]
    def fail(*args):
        calls.append(1)
        raise RuntimeError('test-secret')
    monkeypatch.setattr(canary,'exercise',fail)
    assert canary.main()==1
    assert canary.main()==2
    assert len(calls)==1
    assert 'test-secret' not in capsys.readouterr().out
    assert 'test-secret' not in (tmp_path/'local/openai-canary.json').read_text()
