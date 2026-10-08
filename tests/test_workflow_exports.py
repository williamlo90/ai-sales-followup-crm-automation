import hashlib
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from backend.app import create_app
from scripts.export_workflows import workflow
from scripts.workflow_reference import validate,run
from test_workflows import setup,approve,later


@pytest.mark.parametrize('journey',['intake','due'])
def test_exports_match_generator_and_contract_version(journey):
    doc=json.loads((Path('automation/n8n')/f'{journey}-v1.json').read_text())
    assert doc==workflow(journey)
    validate(doc)
    raw=json.dumps(doc).lower()
    assert 'authorization' not in raw and 'api_key' not in raw and 'webhook' not in raw


def test_export_reference_runner_prepare_wait_approve_execute(lab):
    coordinator,_,_,double=setup(lab)
    client=TestClient(create_app(lab[0],{hashlib.sha256(k.encode()).hexdigest():v for k,v in lab[1].items()},execution=coordinator.execution))
    def wait(seconds,result):
        assert seconds==60
        approve(lab,result['proposal_id']);later(lab,seconds)
    outcome=run(workflow('intake'),client,'worker',wait)
    assert outcome['result']['status']=='completed'
    assert len(outcome['visited'])==5 and double.calls==1


def test_due_export_waits_for_business_eligibility(lab):
    coordinator,_,_,double=setup(lab,'due','email')
    client=TestClient(create_app(lab[0],{hashlib.sha256(k.encode()).hexdigest():v for k,v in lab[1].items()},execution=coordinator.execution))
    def wait(seconds,result):approve(lab,result['proposal_id'],'email');later(lab,seconds)
    assert run(workflow('due'),client,'worker',wait)['result']['status']=='not_due'
    assert double.calls==0


def test_idle_export_stops_without_wait(lab):
    assert run(workflow('intake'),lab[2],'worker',lambda *_:pytest.fail('Unexpected wait'))['result']['status']=='idle'
