from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
import pytest
from backend.domain import DomainError
from backend.skills import SkillService
from backend.workflows import WorkflowService,EnqueueInput
from backend.execution import ExecutionService
from backend.models import ApprovalInput,SourceInput
from backend.sales_rules import Commitment
from doubles import EffectDouble
from conftest import auth


def setup(lab,journey='intake',kind='crm',lose=False):
    sales,actors,_=lab
    sales.commitment(actors['operator'],'deal-1',Commitment(id='c1',revision=1,owner='Sales',description='Confirm demo',
        due_at='2026-10-15T07:00:00Z',observed_at='2026-10-08T10:00:00Z',
        evidence={'source_id':'thread-1','revision':1,'quote':'15 October 2026 at 14:00 Asia/Jakarta'}))
    double=EffectDouble(lose_response=lose)
    executor=ExecutionService(sales,double,enabled=True,send_enabled=True,recipients=frozenset({'customer@example.test'}))
    workflow=WorkflowService(sales,SkillService(sales),executor)
    data=EnqueueInput(journey=journey,kind=kind,deal_id='deal-1',deal_version=1,commitment={'id':'c1','revision':1})
    job=workflow.enqueue(actors['worker'],data)
    return workflow,job,data,double


def later(lab,seconds=61):
    now=lab[0].clock();lab[0].clock=lambda:now+timedelta(seconds=seconds)


def approve(lab,pid,kind='crm'):
    p=lab[0].get(lab[1]['approver'],pid)
    lab[0].approve(lab[1]['approver'],pid,ApprovalInput(kind=kind,payload_hash=p['payload_hash']))


def test_intake_approval_wait_and_duplicate_enqueue(lab):
    workflow,job,data,double=setup(lab)
    assert workflow.enqueue(lab[1]['worker'],data)['id']==job['id']
    first=workflow.tick(lab[1]['worker'],'intake');assert first['status']=='awaiting_approval'
    assert workflow.tick(lab[1]['worker'],'intake')['status']=='idle'
    later(lab);assert workflow.tick(lab[1]['worker'],'intake')['status']=='awaiting_approval'
    approve(lab,first['proposal_id']);later(lab)
    assert workflow.tick(lab[1]['worker'],'intake')['status']=='completed'
    later(lab);assert workflow.tick(lab[1]['worker'],'intake')['status']=='idle'
    assert double.calls==1


def test_due_email_requires_its_own_approval_and_due_time(lab):
    workflow,_,_,double=setup(lab,'intake','email')
    first=workflow.tick(lab[1]['worker'],'intake')
    approve(lab,first['proposal_id'],'crm');later(lab)
    assert workflow.tick(lab[1]['worker'],'intake')['status']=='awaiting_approval'
    approve(lab,first['proposal_id'],'email');later(lab)
    assert workflow.tick(lab[1]['worker'],'intake')['status']=='not_due'
    assert double.calls==0


def test_unknown_readback_after_restart_does_not_dispatch_again(lab):
    workflow,job,_,double=setup(lab,lose=True)
    first=workflow.tick(lab[1]['worker'],'intake');approve(lab,first['proposal_id']);later(lab)
    assert workflow.tick(lab[1]['worker'],'intake')['status']=='unknown'
    restarted=WorkflowService(lab[0],SkillService(lab[0]),workflow.execution);later(lab)
    assert restarted.tick(lab[1]['worker'],'intake')['status']=='completed'
    assert double.calls==1


def test_crash_between_dispatch_and_job_checkpoint_recovers_ledger(lab,monkeypatch):
    workflow,job,_,double=setup(lab)
    first=workflow.tick(lab[1]['worker'],'intake');approve(lab,first['proposal_id']);later(lab)
    original=workflow.advance
    def crash(actor,job):
        result=original(actor,job)
        raise RuntimeError('simulated crash after effect')
    monkeypatch.setattr(workflow,'advance',crash)
    with pytest.raises(RuntimeError):workflow.tick(lab[1]['worker'],'intake')
    restarted=WorkflowService(lab[0],SkillService(lab[0]),workflow.execution)
    assert restarted.tick(lab[1]['worker'],'intake')['status']=='idle'
    later(lab,121)
    assert restarted.tick(lab[1]['worker'],'intake')['status']=='completed'
    assert double.calls==1


def test_concurrent_ticks_one_preparation(lab):
    workflow,_,_,_=setup(lab)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:workflow.tick(lab[1]['worker'],'intake'),range(2)))
    assert sorted(r['status'] for r in results)==['awaiting_approval','idle']


def test_stale_input_enters_review_and_roles_denied(lab):
    workflow,job,data,double=setup(lab)
    lab[0].put_source(lab[1]['worker'],'deal-1',SourceInput(external_id='thread-1',revision=2,occurred_at='2026-10-08T11:00:00Z',text='Cancel.'))
    assert workflow.tick(lab[1]['worker'],'intake')['status']=='review'
    assert double.calls==0
    with pytest.raises(DomainError):workflow.enqueue(lab[1]['operator'],data)
    assert lab[2].post('/v1/workflows/intake/tick',headers=auth('operator')).status_code==403
    assert lab[2].get('/v1/workflows/jobs/'+job['id'],headers=auth('outsider')).status_code==404
