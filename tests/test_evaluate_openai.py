from types import SimpleNamespace
import pytest
from backend.providers import Extraction,ProviderError
from backend.evaluation_budget import EvaluationBudget,BudgetError
from scripts.evaluate_openai import run_case,MODEL
from test_evaluation_scoring import example


class Adapter:
    profile=SimpleNamespace(provider='openai',model=MODEL)
    calls=0
    def extract(self,sources,context):
        self.calls+=1
        return Extraction.model_validate(example()[1]),{'usage':{'input_tokens':100,'output_tokens':100}}


def test_reservation_precedes_call_and_prevents_replay(tmp_path):
    case,_=example();case['context']={};adapter=Adapter();budget=EvaluationBudget(tmp_path/'budget.sqlite')
    result=run_case(case,adapter,budget,'dataset')
    assert result['estimated_actual_microusd']==200
    assert result['score']['automated_pass']
    assert budget.snapshot()['pending']==0
    with pytest.raises(BudgetError,match='already_reserved'):run_case(case,adapter,budget,'dataset')
    assert adapter.calls==1


def test_failed_call_keeps_reservation_and_scores_failure(tmp_path):
    class Broken(Adapter):
        def extract(self,*args):raise ProviderError('model_transport_failure')
    case,_=example();case['context']={};budget=EvaluationBudget(tmp_path/'budget.sqlite')
    result=run_case(case,Broken(),budget,'dataset')
    assert not result['score']['automated_pass']
    assert budget.snapshot()['unknown']==1
    assert budget.snapshot()['committed_microusd']==result['reserved_microusd']


def test_over_budget_never_calls_provider(tmp_path):
    case,_=example();case['context']={};adapter=Adapter()
    with pytest.raises(BudgetError,match='exhausted'):run_case(case,adapter,EvaluationBudget(tmp_path/'budget.sqlite',1),'dataset')
    assert adapter.calls==0


def test_luna_pricing_includes_cache_write_upper_rate(tmp_path):
    class Luna(Adapter):
        profile=SimpleNamespace(provider='openai',model='gpt-5.6-luna',reasoning_effort='low')
    case,_=example();case['context']={}
    result=run_case(case,Luna(),EvaluationBudget(tmp_path/'budget.sqlite'),'dataset','luna-low')
    assert result['estimated_actual_microusd']==145
    assert result['profile']['input_rate']==0.25
    assert result['reserved_microusd']>result['estimated_actual_microusd']


def test_unpriced_reasoning_never_calls(tmp_path):
    adapter=Adapter();adapter.profile=SimpleNamespace(provider='openai',model=MODEL,reasoning_effort='high')
    case,_=example();case['context']={}
    with pytest.raises(ValueError,match='Unpriced'):run_case(case,adapter,EvaluationBudget(tmp_path/'budget.sqlite'),'dataset')
    assert adapter.calls==0


def test_heldout_freeze_rejects_changed_profile():
    from scripts.evaluate_openai import verify_profile_freeze,PROFILES
    from backend.config import ROOT
    verify_profile_freeze(ROOT,PROFILES['luna-low'])
    with pytest.raises(ValueError,match='differs'):
        verify_profile_freeze(ROOT,{**PROFILES['luna-low'],'reasoning':'high'})
