import hashlib
import json
import httpx
import pytest
from fastapi.testclient import TestClient
from backend.app import create_app
from backend.domain import DomainError
from backend.skills import SkillService
from backend.providers import ModelAdapter,ModelProfile
from backend.models import SourceInput
from test_commitment_proposals import bind
from conftest import auth


def model(response,side_effect=None):
    def respond(request):
        if side_effect:side_effect()
        return httpx.Response(200,json={'done':True,'message':{'content':json.dumps(response)}})
    return ModelAdapter(ModelProfile('ollama','test-local',local_only=True,max_calls=5),transport=httpx.MockTransport(respond))


def test_same_prepare_skill_api_and_worker_binding(lab):
    _,p=bind(lab)
    sales,actors,_=lab
    skills=SkillService(sales)
    raw={'deal_id':'deal-1','commitment':{'id':'demo','revision':1},'deal_version':1}
    direct=skills.invoke(actors['operator'],'prepare_crm_update',raw)
    identities={hashlib.sha256(k.encode()).hexdigest():v for k,v in actors.items()}
    client=TestClient(create_app(sales,identities,skills))
    via_api=client.post('/v1/skills/prepare_crm_update',json=raw,headers=auth('operator'))
    assert via_api.status_code==200
    assert via_api.json()['result']['id']==direct['result']['id']==p['id']
    assert skills.invoke(actors['auditor'],'draft_followup',{'proposal_id':p['id']})['result']['send_enabled'] is False


def test_extract_returns_candidates_without_persisting_or_approving(lab):
    c,_=bind(lab)
    payload={'status':'ready','commitments':[c.model_dump(mode='json')],'missing_information':[],'conflicts':[]}
    skills=SkillService(lab[0],model(payload))
    before=len(lab[0].commitments(lab[1]['operator'],'deal-1'))
    result=skills.invoke(lab[1]['operator'],'extract_commitments',{'deal_id':'deal-1'})['result']
    assert result['review_required']
    assert len(lab[0].commitments(lab[1]['operator'],'deal-1'))==before


def test_extracted_foreign_source_is_rejected(lab):
    c,_=bind(lab)
    payload=c.model_dump(mode='json');payload['evidence']['source_id']='private-other-tenant'
    skills=SkillService(lab[0],model({'status':'ready','commitments':[payload],'missing_information':[],'conflicts':[]}))
    with pytest.raises(DomainError,match='model_unsupported_evidence'):
        skills.invoke(lab[1]['operator'],'extract_commitments',{'deal_id':'deal-1'})


def test_context_change_during_inference_requires_review(lab):
    def change():
        lab[0].put_source(lab[1]['worker'],'deal-1',SourceInput(external_id='thread-1',revision=2,occurred_at='2026-10-08T11:00:00Z',text='Cancel.'))
    skills=SkillService(lab[0],model({'status':'review','commitments':[],'missing_information':['date'],'conflicts':[]},change))
    with pytest.raises(DomainError,match='context_changed'):
        skills.invoke(lab[1]['operator'],'extract_commitments',{'deal_id':'deal-1'})


def test_unconfigured_model_and_untrusted_skill_scope(lab):
    client=lab[2]
    assert client.post('/v1/skills/extract_commitments',headers=auth('operator'),json={'deal_id':'deal-1'}).status_code==503
    assert client.post('/v1/skills/extract_commitments',headers=auth('operator'),json={'deal_id':'deal-1','tenant_id':'other'}).status_code==422
    assert client.post('/v1/skills/not_a_skill',headers=auth('operator'),json={}).status_code==404


def test_failed_evidence_validation_has_metadata_trace_without_source_text(lab):
    c,_=bind(lab)
    payload=c.model_dump(mode='json');payload['evidence']['quote']='invented private text'
    skills=SkillService(lab[0],model({'status':'ready','commitments':[payload],'missing_information':[],'conflicts':[]}))
    with pytest.raises(DomainError):skills.invoke(lab[1]['operator'],'extract_commitments',{'deal_id':'deal-1'})
    with lab[0].store.connect() as conn:
        records=[r['metadata'] for r in conn.execute('SELECT metadata FROM model_runs')]
    assert len(records)==1
    assert json.loads(records[0])['error_code']=='model_unsupported_evidence'
    assert 'invented private text' not in records[0]
