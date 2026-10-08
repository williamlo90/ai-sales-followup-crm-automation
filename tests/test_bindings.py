import copy
import hashlib
from datetime import datetime,timezone,timedelta
from uuid import uuid4
import pytest
from backend.bindings import BindingRepository,ConnectorBindingInput
from backend.domain import DomainError,canonical
from backend.models import ProposalInput,SourceInput
from test_odoo_effects import fixture


def setup(lab,proposal):
    sales,actors,_=lab
    local=sales.prepare(actors['operator'],ProposalInput(**proposal))
    repository=BindingRepository(sales,actors['operator'])
    adapter,_,_,binding,state=fixture()
    adapter.deal_mapping={'deal-1':{'opportunity_id':7,'assignee_id':8}}
    binding['preview']['summary']=local['payload']['summary']
    binding['preview']['due_date']=datetime.fromisoformat(local['payload']['due_at']).astimezone(timezone.utc).date().isoformat()
    preview=copy.deepcopy(binding['preview']);digest=hashlib.sha256(canonical(preview).encode()).hexdigest()
    state['workspace']['proposal'].update(preview=preview,payload_hash=digest)
    state['workspace']['approval']['payload_hash']=digest
    data=ConnectorBindingInput.model_validate({k:v for k,v in binding.items() if k!='local_payload_hash'})
    adapter.bindings=repository.load
    return repository,adapter,local,data,state


def test_binding_survives_repository_restart_without_mutation(lab,proposal):
    repo,adapter,local,data,state=setup(lab,proposal)
    saved=repo.attach(local['id'],data,adapter)
    assert saved['local_payload_hash']==local['payload_hash']
    assert repo.attach(local['id'],data,adapter)==saved
    restarted=BindingRepository(lab[0],lab[1]['operator'])
    assert restarted.load('lab',local['id'])==saved
    assert all(method=='GET' for method,path in state['calls'])


def test_same_remote_proposal_cannot_back_two_local_proposals(lab,proposal):
    repo,adapter,local,data,_=setup(lab,proposal);repo.attach(local['id'],data,adapter)
    second=lab[0].prepare(lab[1]['operator'],ProposalInput(**{**proposal,'draft':'Different draft'}))
    with pytest.raises(DomainError,match='already_bound'):repo.attach(second['id'],data,adapter)


def test_binding_cannot_be_replaced_even_with_valid_other_approval(lab,proposal):
    repo,adapter,local,data,state=setup(lab,proposal);repo.attach(local['id'],data,adapter)
    replacement=str(uuid4());state['workspace']['approval']['id']=replacement
    changed=ConnectorBindingInput.model_validate({**data.model_dump(mode='json'),'approval_id':replacement})
    with pytest.raises(DomainError,match='immutable'):repo.attach(local['id'],changed,adapter)
    assert repo.load('lab',local['id'])['approval_id']==str(data.approval_id)


def test_context_change_during_remote_validation_rolls_back_binding(lab,proposal,monkeypatch):
    repo,adapter,local,data,_=setup(lab,proposal)
    original=adapter.workspace
    def change(binding,**kwargs):
        result=original(binding,**kwargs)
        lab[0].put_source(lab[1]['worker'],'deal-1',SourceInput(external_id='thread-1',revision=2,
            occurred_at='2026-10-08T11:00:00Z',text='Cancel the request.'))
        return result
    monkeypatch.setattr(adapter,'workspace',change)
    with pytest.raises(DomainError,match='source_changed'):repo.attach(local['id'],data,adapter)
    with pytest.raises(DomainError,match='binding_missing'):repo.load('lab',local['id'])


def test_repository_scope_and_expired_readback_payload(lab,proposal):
    repo,adapter,local,data,_=setup(lab,proposal);repo.attach(local['id'],data,adapter)
    with pytest.raises(DomainError):BindingRepository(lab[0],lab[1]['auditor']).attach(local['id'],data,adapter)
    with pytest.raises(DomainError,match='record_not_found'):repo.payload('other',local['id'])
    other=BindingRepository(lab[0],lab[1]['worker'])
    with pytest.raises(DomainError,match='owner_required'):other.attach(local['id'],data,adapter)
    now=lab[0].clock();lab[0].clock=lambda:now+timedelta(days=2)
    assert repo.payload('lab',local['id'])==local['payload']
    assert repo.load('lab',local['id'])['local_payload_hash']==local['payload_hash']
    with pytest.raises(DomainError,match='expired'):repo.attach(local['id'],data,adapter)


def test_already_executed_connector_cannot_be_adopted(lab,proposal):
    repo,adapter,local,data,state=setup(lab,proposal);state['workspace']['operation']=state['remote']
    with pytest.raises(DomainError,match='already_executed'):repo.attach(local['id'],data,adapter)


def test_binding_api_default_off_and_scoped_read(lab,proposal):
    from backend.app import create_app
    from fastapi.testclient import TestClient
    from conftest import auth
    repo,adapter,local,data,state=setup(lab,proposal)
    path=f"/v1/proposals/{local['id']}/connector-binding"
    assert lab[2].post(path,headers=auth('operator'),json=data.model_dump(mode='json')).json()['error']=='connector_not_configured'
    assert not state['calls']
    client=TestClient(create_app(lab[0],{hashlib.sha256(k.encode()).hexdigest():v for k,v in lab[1].items()},connector=adapter))
    assert client.post(path,headers=auth('auditor'),json=data.model_dump(mode='json')).status_code==403
    assert client.post(path,headers=auth('operator'),json=data.model_dump(mode='json')).status_code==200
    assert client.get(path,headers=auth('approver')).json()['local_payload_hash']==local['payload_hash']
    assert client.get(path,headers=auth('outsider')).status_code==404
    assert all(method=='GET' for method,path in state['calls'])
