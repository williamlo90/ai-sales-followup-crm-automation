import pytest
from backend.models import PrepareCommitmentInput, ApprovalInput, ProposalInput
from backend.domain import DomainError
from backend.execution import ExecutionService
from backend.sales_rules import Commitment
from doubles import EffectDouble
from conftest import auth


def bind(lab):
    service,actors,_=lab
    candidate=Commitment.model_validate({"id":"demo","revision":1,"owner":"sales","description":"Confirm demo",
        "due_at":"2026-10-15T14:00:00+07:00","observed_at":"2026-10-08T10:00:00Z",
        "evidence":{"source_id":"thread-1","revision":1,"quote":"15 October 2026 at 14:00 Asia/Jakarta"}})
    service.commitment(actors['operator'],'deal-1',candidate)
    p=service.prepare_commitment(actors['operator'],'deal-1',PrepareCommitmentInput(commitment={"id":"demo","revision":1},deal_version=1))
    return candidate,p


def test_bound_proposal_uses_candidate_and_requires_review(lab):
    candidate,p=bind(lab)
    assert p['payload']['commitment']=={'id':'demo','revision':1}
    assert p['payload']['due_at']==candidate.model_dump(mode='json')['due_at']
    assert candidate.evidence.quote in p['payload']['draft']
    assert p['approvals']==[]
    assert p['draft_validation']=='human_review_required'


def test_candidate_change_invalidates_approval_even_without_source_change(lab):
    c,p=bind(lab)
    service,actors,_=lab
    service.approve(actors['approver'],p['id'],ApprovalInput(kind='crm',payload_hash=p['payload_hash']))
    service.commitment(actors['operator'],'deal-1',c.model_copy(update={'revision':2,'supersedes':1,'state':'cancelled'}))
    assert service.get(actors['operator'],p['id'])['validation_error']=='commitment_changed'
    with pytest.raises(DomainError,match='commitment_cancelled'):
        service.prepare_commitment(actors['operator'],'deal-1',PrepareCommitmentInput(commitment={'id':'demo','revision':2},deal_version=1))


def test_cannot_change_bound_due_date(lab,proposal):
    bind(lab)
    proposal['commitment']={'id':'demo','revision':1}
    proposal['due_at']='2026-10-16T14:00:00+07:00'
    with pytest.raises(DomainError,match='commitment_payload_mismatch'):
        lab[0].prepare(lab[1]['operator'],ProposalInput(**proposal))


def test_revision_after_completed_action_needs_review_not_second_creation(lab):
    c,p=bind(lab)
    service,actors,_=lab
    service.approve(actors['approver'],p['id'],ApprovalInput(kind='crm',payload_hash=p['payload_hash']))
    double=EffectDouble()
    executor=ExecutionService(service,double,enabled=True)
    executor.execute(actors['operator'],p['id'],'crm')
    service.commitment(actors['operator'],'deal-1',c.model_copy(update={'revision':2,'supersedes':1,'description':'Confirm revised demo'}))
    revised=service.prepare_commitment(actors['operator'],'deal-1',PrepareCommitmentInput(commitment={'id':'demo','revision':2},deal_version=1))
    service.approve(actors['approver'],revised['id'],ApprovalInput(kind='crm',payload_hash=revised['payload_hash']))
    with pytest.raises(DomainError,match='revision_update_requires_review'):
        executor.execute(actors['operator'],revised['id'],'crm')
    assert double.calls==1


def test_operation_read_is_scoped_and_reports_unknown(lab):
    _,p=bind(lab)
    service,actors,client=lab
    service.approve(actors['approver'],p['id'],ApprovalInput(kind='crm',payload_hash=p['payload_hash']))
    executor=ExecutionService(service,EffectDouble(lose_response=True),enabled=True)
    op=executor.execute(actors['operator'],p['id'],'crm')
    response=client.get('/v1/operations/'+op['id'],headers=auth('auditor'))
    assert response.status_code==200
    assert response.json()['recovery']=='reconcile_before_retry'
    assert client.get('/v1/operations/'+op['id'],headers=auth('outsider')).status_code==404
    assert len(client.get(f"/v1/proposals/{p['id']}/operations",headers=auth('operator')).json()['items'])==1
