from types import SimpleNamespace
import pytest
from backend.budgeted_model import BudgetedModel
from backend.evaluation_budget import EvaluationBudget
from backend.providers import ModelProfile, ProviderError

class Adapter:
    profile=ModelProfile('openai','gpt-5.6-luna',reasoning_effort='low')
    calls=0
    fail=False
    def extract(self,*args):
        self.calls+=1
        if self.fail:raise ProviderError('timeout')
        return 'result',{'usage':{'input_tokens':100,'output_tokens':10}}

def test_budget_survives_new_adapter_and_denies_before_network(tmp_path):
    path=tmp_path/'budget.sqlite';a=Adapter()
    budget=EvaluationBudget(path,cap_microusd=15000)
    result,trace=BudgetedModel(a,budget).extract([], {})
    assert trace=={'usage':{'input_tokens':100,'output_tokens':10}}
    restarted=BudgetedModel(a,EvaluationBudget(path,cap_microusd=15000))
    with pytest.raises(ProviderError,match='persistent_budget_denied'):
        for _ in range(3):restarted.extract([],{})
    assert a.calls==1
    assert budget.snapshot()['calls']==1

def test_unknown_usage_keeps_full_reservation(tmp_path):
    a=Adapter();a.fail=True;b=EvaluationBudget(tmp_path/'budget.sqlite')
    with pytest.raises(ProviderError,match='timeout'):BudgetedModel(a,b).extract([],{})
    snapshot=b.snapshot()
    assert snapshot['unknown']==1 and snapshot['pending']==0
    assert snapshot['committed_microusd']>0

def test_oversize_and_unpriced_profile_do_not_reserve(tmp_path):
    b=EvaluationBudget(tmp_path/'budget.sqlite');a=Adapter()
    with pytest.raises(ProviderError,match='budget_input_limit'):BudgetedModel(a,b).extract([],{ 'text':'x'*16001})
    a.profile=ModelProfile('openai','unpriced')
    with pytest.raises(ProviderError,match='unpriced_connected_profile'):BudgetedModel(a,b)
    assert a.calls==0 and b.snapshot()['calls']==0

def test_budget_wrapper_preserves_skill_output_contract(lab,tmp_path):
    import json,httpx
    from backend.providers import ModelAdapter
    from backend.skills import SkillService
    from test_providers import envelope,REVIEW
    from test_commitment_proposals import bind
    bind(lab)
    adapter=ModelAdapter(ModelProfile('openai','gpt-5.6-luna',key='test-only',max_calls=1,reasoning_effort='low'),transport=httpx.MockTransport(lambda request:httpx.Response(200,json=envelope('openai',json.dumps(REVIEW)))))
    budget=EvaluationBudget(tmp_path/'budget.sqlite')
    service=SkillService(lab[0],BudgetedModel(adapter,budget))
    result=service.invoke(lab[1]['operator'],'extract_commitments',{'deal_id':'deal-1'})
    assert result['result']['extraction']['status']=='review'
    assert budget.snapshot()['calls']==1
