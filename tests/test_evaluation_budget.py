from concurrent.futures import ThreadPoolExecutor
import pytest
from backend.evaluation_budget import EvaluationBudget,BudgetError


def test_restart_unknown_and_replay_keep_reservation(tmp_path):
    path=tmp_path/'budget.sqlite';budget=EvaluationBudget(path,100)
    budget.reserve('one','model/dataset/case',60)
    restarted=EvaluationBudget(path,100)
    with pytest.raises(BudgetError,match='in_flight'):restarted.reserve('two','metadata',20)
    restarted.finish('one')
    with pytest.raises(BudgetError,match='already_reserved'):restarted.reserve('one','metadata',1)
    with pytest.raises(BudgetError,match='exhausted'):restarted.reserve('two','metadata',41)
    assert restarted.snapshot()['unknown']==1


def test_actual_cost_does_not_free_reservation(tmp_path):
    budget=EvaluationBudget(tmp_path/'budget.sqlite',100)
    budget.reserve('one','metadata',60);budget.finish('one',10);budget.finish('one',10)
    assert budget.snapshot()['remaining_microusd']==40
    with pytest.raises(BudgetError,match='immutable'):budget.finish('one',0)
    with pytest.raises(BudgetError,match='immutable'):EvaluationBudget(budget.path,200)


def test_concurrent_reservations_serialize(tmp_path):
    budget=EvaluationBudget(tmp_path/'budget.sqlite',100)
    def reserve(ident):
        try:budget.reserve(ident,'metadata',60);return 'reserved'
        except BudgetError:return 'denied'
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(reserve,['one','two']))
    assert sorted(results)==['denied','reserved']
    assert budget.snapshot()['committed_microusd']==60


def test_observed_overrun_is_preserved(tmp_path):
    budget=EvaluationBudget(tmp_path/'budget.sqlite',100)
    budget.reserve('one','metadata',60);budget.finish('one',110)
    assert budget.snapshot()['overrun']
    assert budget.snapshot()['reported_actual_microusd']==110
    with pytest.raises(BudgetError,match='overrun'):budget.reserve('two','metadata',1)


@pytest.mark.parametrize('value',[True,-1,1.5,'10'])
def test_invalid_amount_never_reserves(tmp_path,value):
    budget=EvaluationBudget(tmp_path/'budget.sqlite',100)
    with pytest.raises(BudgetError):budget.reserve('one','metadata',value)
    assert budget.snapshot()['calls']==0
