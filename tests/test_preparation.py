import hashlib
import httpx
import pytest
from fastapi.testclient import TestClient
from backend.app import create_app
from backend.models import SourceInput
from backend.domain import DomainError
from backend.read_clients import ReadError
from test_bindings import setup
from conftest import auth


def test_preparation_uses_shared_mapping_and_read_only_connector(lab,proposal):
    repo,adapter,local,_,state=setup(lab,proposal)
    calls=[]
    def handler(request):
        calls.append((request.method,request.url.path))
        if request.url.path=='/me':return httpx.Response(200,json={'tenant_id':adapter.client.tenant_id,'role':'operator'})
        return httpx.Response(200,json={'id':7,'company_id':2,'source':'odoo:crm.lead','version':'current-version'})
    adapter.client.reader.transport=httpx.MockTransport(handler)
    result=repo.preparation(local['id'],adapter)
    assert result['preview']['summary']==proposal['summary']
    assert result['opportunity_version']=='current-version'
    assert 'source_version' not in result['preview']
    assert result['connector_preparation_required'] is True
    assert result['write_performed'] is False
    with pytest.raises(ReadError,match='activity_preview_mismatch'):
        adapter.validate_activity(local['payload'],{'preview':result['preview']})
    assert calls==[('GET','/me'),('GET','/v1/opportunities/7')]


def test_preparation_rechecks_source_after_connector_latency(lab,proposal,monkeypatch):
    repo,adapter,local,_,_=setup(lab,proposal)
    def changed(payload):
        lab[0].put_source(lab[1]['worker'],'deal-1',SourceInput(external_id='thread-1',revision=2,occurred_at='2026-10-08T11:00:00Z',text='Cancelled'))
        return {}
    monkeypatch.setattr(adapter,'preparation',changed)
    with pytest.raises(DomainError,match='source_changed'):repo.preparation(local['id'],adapter)


@pytest.mark.parametrize('workers',[0,2])
def test_handoff_missing_or_ambiguous_worker_fails_closed(lab,workers):
    from test_handoff import prepared
    _,proposal=prepared(lab)
    identities={hashlib.sha256(b'operator').hexdigest():lab[1]['operator']}
    for i in range(workers):identities[hashlib.sha256(str(i).encode()).hexdigest()]=lab[1]['worker'].model_copy(update={'id':f'worker-{i}'})
    client=TestClient(create_app(lab[0],identities))
    response=client.post(f"/v1/proposals/{proposal['id']}/handoff/crm",headers=auth('operator'))
    assert response.status_code==503
    assert response.json()['error']=='workflow_worker_configuration_required'
