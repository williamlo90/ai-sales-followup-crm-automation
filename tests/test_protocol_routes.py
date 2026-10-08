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
