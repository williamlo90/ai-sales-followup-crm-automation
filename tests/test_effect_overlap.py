import pytest
from concurrent.futures import ThreadPoolExecutor
from backend.domain import DomainError
from backend.execution import ExecutionService
from backend.models import ProposalInput, ApprovalInput, PrepareCommitmentInput
from test_commitment_proposals import bind
from doubles import EffectDouble


@pytest.mark.parametrize('manual_first',[True,False])
@pytest.mark.parametrize('unknown',[True,False])
def test_manual_bound_overlap_never_dispatches_twice(lab,manual_first,unknown):
    sales,actors,_=lab
    _,bound=bind(lab)
    raw={k:v for k,v in bound['payload'].items() if k in ProposalInput.model_fields}
    raw['commitment']=None
    manual=sales.prepare(actors['operator'],ProposalInput(**raw))
    for p in [manual,bound]:sales.approve(actors['approver'],p['id'],ApprovalInput(kind='crm',payload_hash=p['payload_hash']))
    double=EffectDouble(lose_response=unknown);executor=ExecutionService(sales,double,enabled=True)
    first,second=(manual,bound) if manual_first else (bound,manual)
    executor.execute(actors['operator'],first['id'],'crm')
    with pytest.raises(DomainError,match='effect_overlap_requires_review'):
        executor.execute(actors['operator'],second['id'],'crm')
    assert sales.due(actors['operator'],second['id'],'crm')['reason']=='effect_overlap_requires_review'
    assert double.calls==1


def test_new_commitment_id_cannot_duplicate_same_evidence(lab):
    sales,actors,_=lab;c,p=bind(lab)
    sales.approve(actors['approver'],p['id'],ApprovalInput(kind='crm',payload_hash=p['payload_hash']))
    double=EffectDouble();executor=ExecutionService(sales,double,enabled=True)
    executor.execute(actors['operator'],p['id'],'crm')
    sales.commitment(actors['operator'],'deal-1',c.model_copy(update={'id':'alias'}))
    alias=sales.prepare_commitment(actors['operator'],'deal-1',PrepareCommitmentInput(commitment={'id':'alias','revision':1},deal_version=1))
    sales.approve(actors['approver'],alias['id'],ApprovalInput(kind='crm',payload_hash=alias['payload_hash']))
    with pytest.raises(DomainError,match='effect_overlap_requires_review'):executor.execute(actors['operator'],alias['id'],'crm')
    assert double.calls==1


def test_concurrent_manual_bound_prepare_one_effect(lab):
    sales,actors,_=lab;_,bound=bind(lab)
    raw={k:v for k,v in bound['payload'].items() if k in ProposalInput.model_fields}
    raw['commitment']=None
    manual=sales.prepare(actors['operator'],ProposalInput(**raw))
    for p in [manual,bound]:sales.approve(actors['approver'],p['id'],ApprovalInput(kind='crm',payload_hash=p['payload_hash']))
    double=EffectDouble();executor=ExecutionService(sales,double,enabled=True)
    def dispatch(p):
        try:return executor.execute(actors['operator'],p['id'],'crm')['status']
        except DomainError as exc:return exc.code
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(dispatch,[manual,bound]))
    assert sorted(results)==['effect_overlap_requires_review','verified']
    assert double.calls==1
