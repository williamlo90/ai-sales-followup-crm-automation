import hashlib
import json
from pathlib import Path
from fastapi.testclient import TestClient
from backend.app import create_app
from backend.execution import ExecutionService
from backend.models import ProposalInput, ApprovalInput
from backend.skills import SkillService
from backend.skill_outputs import OUTPUTS
from conftest import auth
from doubles import EffectDouble


def test_execution_api_uses_core_approval_replay_and_readback(lab,proposal):
    sales,actors,_=lab
    p=sales.prepare(actors['operator'],ProposalInput(**proposal))
    double=EffectDouble(lose_response=True)
    execution=ExecutionService(sales,double,enabled=True)
    client=TestClient(create_app(sales,{hashlib.sha256(k.encode()).hexdigest():v for k,v in actors.items()},execution=execution))
    path=f"/v1/proposals/{p['id']}/execute/crm"
    assert client.post(path,headers=auth('operator')).json()['error']=='approval_required'
    sales.approve(actors['approver'],p['id'],ApprovalInput(kind='crm',payload_hash=p['payload_hash']))
    result=client.post(path,headers=auth('operator')).json()
    assert result['status']=='unknown'
    assert client.post(path,headers=auth('operator')).json()['id']==result['id']
    observed=client.post('/v1/skills/reconcile_followup',headers=auth('operator'),json={'operation_id':result['id']})
    assert observed.status_code==200
    assert observed.json()['result']['status']=='verified'
    assert double.calls==1
    assert client.post(path,headers=auth('auditor')).status_code==403


def test_context_scopes_and_complete_output_schema(lab):
    assert lab[2].get('/v1/deals/deal-1/context',headers=auth('outsider')).status_code==404
    assert lab[2].get('/v1/deals/deal-1/context',headers=auth('operator')).status_code==200
    for name,contract in OUTPUTS.items():
        exported=json.loads((Path('skills')/name/'output.schema.json').read_text())
        expected=contract.model_json_schema();definitions=expected.pop('$defs',{})
        assert exported['properties']['result']==expected
        assert exported['$defs']==definitions


def test_selected_graph_ingest_route_requires_configured_worker(lab):
    sales, actors, _ = lab
    class Ingestion:
        actor = actors['worker']
        def selected(self, ident):
            return {'external_id': ident, 'changed': 1, 'checkpoint_advanced': False}
    client = TestClient(create_app(sales, {hashlib.sha256(k.encode()).hexdigest(): v
                                           for k, v in actors.items()}, ingestion=Ingestion()))
    path = '/v1/ingest/graph/selected'
    assert client.post(path, headers=auth('operator'), json={'id': 'm1'}).status_code == 403
    assert client.post(path, headers=auth('outsider'), json={'id': 'm1'}).status_code == 403
    assert client.post(path, headers=auth('worker'), json={'id': 'm1', 'extra': True}).status_code == 422
    result = client.post(path, headers=auth('worker'), json={'id': 'm1'})
    assert result.status_code == 200 and result.json()['checkpoint_advanced'] is False


def test_readiness_reports_configured_adapters_without_claiming_network_health(lab):
    sales, _, client = lab
    offline = client.get('/health/ready')
    assert offline.status_code == 200
    assert offline.json()['connectors_configured'] == {'odoo': False, 'graph': False}
    assert 'connected' not in offline.json()
    configured = TestClient(create_app(sales, {}, connector=object(), ingestion=object()))
    ready = configured.get('/health/ready')
    assert ready.status_code == 200
    assert ready.json()['connectors_configured'] == {'odoo': True, 'graph': True}
    assert ready.json()['send_enabled'] is False
