import json
from pathlib import Path
from backend.evaluation_pipeline import exercise


def case_and_response(index=0):
    case=json.loads(Path('fixtures/evaluation/development-v2.json').read_text())['cases'][index]
    labels=case['expected']['commitments'];commitments=[]
    for label in labels:
        source=next(s for s in case['sources'] if s['external_id']==label['source_id'])
        commitments.append({**{k:v for k,v in label.items() if k!='source_id'},'id':label['id'] or 'new-commitment',
            'description':'Next step','observed_at':source['occurred_at'],
            'evidence':{'source_id':source['external_id'],'revision':source['revision'],'quote':source['text']}})
    return case,{'status':case['expected']['status'],'commitments':commitments,
                'missing_information':case['expected']['missing_information'],'conflicts':[]}


def test_actual_core_produces_reviewable_proposal_without_effect(tmp_path):
    case,raw=case_and_response();result=exercise(case,raw,tmp_path/'core.sqlite')
    assert result['linkage_correct'] and result['error'] is None
    p=result['proposals'][0]
    assert p['payload']['due_at']=='2026-11-02T09:00:00Z'
    assert p['payload']['recipient']=='evaluation-recipient@example.test'
    assert case['sources'][0]['text'] in p['payload']['draft']
    assert p['approval_count']==0 and result['no_unauthorized_effect']


def test_revision_history_uses_actual_merge_rules(tmp_path):
    case,raw=case_and_response(2);result=exercise(case,raw,tmp_path/'revision.sqlite')
    assert result['error'] is None
    assert result['proposals'][0]['payload']['commitment']['revision']==2


def test_cancellation_and_ambiguity_do_not_prepare(tmp_path):
    for index in [18,15]:
        case,raw=case_and_response(index);result=exercise(case,raw,tmp_path/f'case-{index}.sqlite')
        assert not result['proposals'] and result['no_unauthorized_effect']
        assert result['error'] is None


def test_unsupported_model_evidence_rejected_by_core(tmp_path):
    case,raw=case_and_response();raw['commitments'][0]['evidence']['quote']='invented'
    result=exercise(case,raw,tmp_path/'rejected.sqlite')
    assert result['error']=='unsupported_evidence' and not result['proposals']
