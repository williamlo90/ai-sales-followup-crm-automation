import json
import pytest
from test_evaluation_pipeline import case_and_response
from backend.evaluation_pipeline import exercise
from backend.evaluation_scoring import score_extraction
from scripts.replay_phase6 import check_case, digest


@pytest.mark.parametrize('change', [None, 'response', 'payload', 'score', 'count', 'dataset'])
def test_replay_detects_material_drift_but_ignores_random_proposal_id(tmp_path, change):
    case, response = case_and_response()
    record = {'case_id': case['id'], 'dataset_sha256': 'synthetic-test', 'profile': {},
              'response': response, 'score': score_extraction(case, response),
              'pipeline': exercise(case, response, tmp_path/'original.sqlite')}
    review = {'case_id': case['id'], 'response_sha256': digest(json.dumps(response, sort_keys=True).encode()),
              'automated_pass': record['score']['automated_pass'], 'semantic_review_pass': False,
              'proposal_count': len(record['pipeline']['proposals'])}
    if change == 'response': record['response']['commitments'][0]['owner'] = 'invented'
    if change == 'payload': record['pipeline']['proposals'][0]['payload']['recipient'] = 'wrong@example.test'
    if change == 'score': record['score']['automated_pass'] = False
    if change == 'count': review['proposal_count'] = 0
    if change == 'dataset': record['dataset_sha256'] = 'changed'
    args = (case, record, review, 'synthetic-test', {}, tmp_path/'replay.sqlite')
    if change is None:
        result = check_case(*args)
        assert result['core_unchanged'] and result['recorded_semantic_review_pass'] is False
    else:
        with pytest.raises(ValueError): check_case(*args)
