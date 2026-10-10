"""Offline replay of accepted responses; never new model or human evidence."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from backend.config import ROOT
from backend.evaluation_pipeline import exercise
from backend.evaluation_scoring import score_extraction
from scripts.evaluate_openai import verify_profile_freeze, PROFILES


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def stable_pipeline(record):
    result = copy.deepcopy(record)
    for proposal in result['proposals']:
        # Proposal UUID is deliberately generated on each isolated replay.
        proposal.pop('id')
    return result


def check_case(case, record, review, dataset_hash, profile, path):
    if record['case_id'] != case['id'] or review['case_id'] != case['id']:
        raise ValueError('Case identity mismatch')
    if record['dataset_sha256'] != dataset_hash or record['profile'] != profile:
        raise ValueError('Dataset/profile mismatch')
    if digest(json.dumps(record['response'], sort_keys=True).encode()) != review['response_sha256']:
        raise ValueError('Reviewed response mismatch')
    scored = score_extraction(case, record['response'])
    if scored != record['score'] or scored['automated_pass'] != review['automated_pass']:
        raise ValueError('Scoring changed')
    replayed = exercise(case, record['response'], path)
    if stable_pipeline(replayed) != stable_pipeline(record['pipeline']):
        raise ValueError('Core replay changed')
    if len(replayed['proposals']) != review['proposal_count']:
        raise ValueError('Published proposal count mismatch')
    return {'case_id': case['id'], 'scorer_unchanged': True, 'core_unchanged': True,
            'recorded_semantic_review_pass': review['semantic_review_pass']}


def replay(root=ROOT):
    profile = PROFILES['luna-low']
    verify_profile_freeze(root, profile)
    manifest = json.loads((root/'docs/phase-6/dataset-freeze.json').read_text())
    if digest((root/'backend/evaluation_scoring.py').read_bytes()) != manifest['scorer_sha256']:
        raise ValueError('Frozen scorer changed')
    cases = []
    with TemporaryDirectory(prefix='sales-offline-replay-') as temp:
        for split in ('development', 'heldout'):
            relative = f'fixtures/evaluation/{split}-v2.json'
            raw = (root/relative).read_bytes(); dataset_hash = digest(raw)
            if dataset_hash != manifest['dataset_files'][relative]:
                raise ValueError('Frozen dataset changed')
            dataset = json.loads(raw)['cases']
            report = json.loads((root/f'docs/evidence/phase-6-{split}-luna.json').read_text())
            reviews = report['cases']
            if report['dataset_sha256'] != dataset_hash or [r['case_id'] for r in reviews] != [c['id'] for c in dataset]:
                raise ValueError('Published report identity mismatch')
            for case, review in zip(dataset, reviews):
                source = root/'local/phase-6'/f"{profile['version']}-{dataset_hash[:16]}-{case['id']}.json"
                record_bytes = source.read_bytes()
                result = check_case(case, json.loads(record_bytes), review, dataset_hash, profile, Path(temp)/f"{case['id']}.sqlite")
                cases.append(result | {'raw_record_sha256': digest(record_bytes)})
    return {'scope': 'Offline replay of previously observed OpenAI responses through current scorer/core; no new inference, semantic review or human session.',
            'code_revision': subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
            'total': len(cases), 'unchanged': len(cases), 'cases': cases,
            'phase6_complete': False,
            'remaining': ['Claude/Grok real comparison', 'Observed waiting-time comparison', 'Final candidate audit/freeze']}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); result = replay()
    with args.output.open('x', encoding='utf-8') as target:
        json.dump(result, target, indent=2)
    print(json.dumps({'total': result['total'], 'unchanged': result['unchanged'], 'phase6_complete': False}))


if __name__ == '__main__':
    main()
