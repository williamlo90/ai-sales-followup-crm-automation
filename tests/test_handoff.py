import pytest
from backend.models import PrepareCommitmentInput, SourceInput
from backend.domain import DomainError
from test_workflows import setup
from conftest import auth


def prepared(lab):
    workflow,_,data,_=setup(lab)
    p=lab[0].prepare_commitment(lab[1]['operator'],'deal-1',PrepareCommitmentInput(
        commitment=data.commitment,deal_version=1))
    return workflow,p


def test_handoff_preserves_reviewed_proposal_and_is_idempotent(lab):
    workflow,p=prepared(lab)
    client=lab[2]
    route=f"/v1/proposals/{p['id']}/handoff/crm"
    response=client.post(route,headers=auth('operator'))
    assert response.status_code==201,response.text
    job=response.json()
    assert job['proposal_id']==p['id']
    assert client.post(route,headers=auth('operator')).json()['id']==job['id']
    with lab[0].store.connect() as conn:
        row=conn.execute('SELECT * FROM workflow_jobs WHERE id=?',(job['id'],)).fetchone()
        assert row['worker_id']=='worker'
    assert workflow.advance(lab[1]['worker'],dict(row))=={'status':'awaiting_approval'}
    assert lab[0].get(lab[1]['operator'],p['id'])['approvals']==[]
    assert client.post(f"/v1/proposals/{p['id']}/handoff/email",headers=auth('operator')).json()['id']!=job['id']


@pytest.mark.parametrize('role',['approver','auditor','worker','outsider','unscoped'])
def test_handoff_rejects_non_owner_roles(lab,role):
    _,p=prepared(lab)
    assert lab[2].post(f"/v1/proposals/{p['id']}/handoff/crm",headers=auth(role)).status_code in {403,404}


def test_handoff_rejects_stale_evidence(lab):
    workflow,p=prepared(lab)
    lab[0].put_source(lab[1]['worker'],'deal-1',SourceInput(external_id='thread-1',revision=2,
        occurred_at='2026-10-08T11:00:00Z',text='Cancel the demo.'))
    with pytest.raises(DomainError):workflow.handoff(lab[1]['operator'],p['id'],lab[1]['worker'],'crm')
