from datetime import timedelta
import pytest
from backend.domain import DomainError
from backend.workflows import WorkflowService
from backend.skills import SkillService
from test_workflows import setup,later,approve
from conftest import auth


def test_future_due_job_does_not_age_a_proposal(lab):
    workflow,job,_,_=setup(lab,'due','email')
    result=workflow.tick(lab[1]['worker'],'due')
    assert result['status']=='not_due' and result['proposal_id'] is None
    assert not lab[0].list(lab[1]['operator'])
    later(lab,7*86400)
    assert workflow.tick(lab[1]['worker'],'due')['status']=='awaiting_approval'


def test_due_discovery_latest_scope_and_replay(lab):
    workflow,_,_,_=setup(lab,'intake','crm')
    assert workflow.discover_due(lab[1]['worker'])['job_ids']==[]
    later(lab,7*86400)
    result=workflow.discover_due(lab[1]['worker'],limit=1)
    assert len(result['job_ids'])==1 and result['cycle_complete'] is False
    assert workflow.discover_due(lab[1]['worker'],limit=1)['cycle_complete']
    assert workflow.discover_due(lab[1]['worker'],limit=1)['job_ids']==result['job_ids']
    with pytest.raises(DomainError):workflow.discover_due(lab[1]['operator'])


def test_expired_proposal_renewal_never_reuses_approval(lab):
    workflow,job,_,_=setup(lab)
    first=workflow.tick(lab[1]['worker'],'intake');approve(lab,first['proposal_id'])
    later(lab,2*86400)
    assert workflow.tick(lab[1]['worker'],'intake')['error_code']=='proposal_expired'
    workflow.recover(lab[1]['operator'],job['id'],'renew_expired')
    renewed=workflow.tick(lab[1]['worker'],'intake')
    assert renewed['proposal_id']!=first['proposal_id']
    assert not lab[0].get(lab[1]['operator'],renewed['proposal_id'])['approvals']


def test_unknown_recovery_is_observation_only(lab,monkeypatch):
    workflow,job,_,double=setup(lab,lose=True)
    first=workflow.tick(lab[1]['worker'],'intake');approve(lab,first['proposal_id']);later(lab)
    workflow.tick(lab[1]['worker'],'intake')
    for action in ['renew_expired','recheck']:
        with pytest.raises(DomainError,match='reconciliation_required'):workflow.recover(lab[1]['operator'],job['id'],action)
    workflow.recover(lab[1]['operator'],job['id'],'observe')
    assert workflow.tick(lab[1]['worker'],'intake')['status']=='completed'
    assert double.calls==1


def test_recovery_api_scope_and_read_only_roles(lab):
    workflow,job,_,_=setup(lab)
    assert lab[2].get('/v1/workflows/jobs',headers=auth('operator')).json()['items'][0]['id']==job['id']
    assert lab[2].get('/v1/workflows/jobs',headers=auth('outsider')).json()['items']==[]
    assert lab[2].post('/v1/workflows/jobs/'+job['id']+'/recover',headers=auth('approver'),json={'action':'recheck'}).status_code==403


def test_cancelled_latest_commitment_is_not_discovered(lab):
    from backend.sales_rules import Commitment
    workflow,_,_,_=setup(lab)
    current=Commitment.model_validate(lab[0].commitments(lab[1]['operator'],'deal-1')[0])
    lab[0].commitment(lab[1]['operator'],'deal-1',current.model_copy(update={'revision':2,'supersedes':1,'state':'cancelled'}))
    later(lab,7*86400)
    assert workflow.discover_due(lab[1]['worker'])['job_ids']==[]
