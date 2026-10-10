"""One explicit local development case. Never downloads, launches or falls back."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory
import httpx
from backend.config import ROOT
from backend.providers import ModelAdapter,ModelProfile,ProviderError,SYSTEM,wire_schema
from backend.evaluation_scoring import score_extraction
from backend.evaluation_pipeline import exercise

MODEL='qwen3:1.7b'
RUNTIME='0.40.2'


def check_metadata(version,tags,show,digest):
    if not re.fullmatch(r'[0-9a-f]{64}',digest) or not digest.startswith('8f68893c685c'):raise ValueError('Unpinned model digest')
    if version.get('version')!=RUNTIME:raise ValueError('Runtime version mismatch')
    matches=[m for m in tags.get('models',[]) if m.get('name')==MODEL and m.get('digest')==digest]
    if len(matches)!=1:raise ValueError('Installed model does not match pin')
    values=show.get('thinking',{}).get('values',[])
    if not any(value is False for value in values):raise ValueError('Explicit non-thinking support unverified')


def main():
    p=argparse.ArgumentParser();p.add_argument('--case',required=True);p.add_argument('--model-digest',required=True);p.add_argument('--run',action='store_true');args=p.parse_args()
    data=(ROOT/'fixtures/evaluation/development-v2.json').read_bytes();digest=hashlib.sha256(data).hexdigest()
    freeze=json.loads((ROOT/'docs/phase-6/dataset-freeze.json').read_text())
    if digest!=freeze['dataset_files']['fixtures/evaluation/development-v2.json']:raise ValueError('Dataset changed')
    if hashlib.sha256((ROOT/'backend/evaluation_scoring.py').read_bytes()).hexdigest()!=freeze['scorer_sha256']:raise ValueError('Scorer changed')
    case=next(c for c in json.loads(data)['cases'] if c['id']==args.case)
    if not re.fullmatch(r'[0-9a-f]{64}',args.model_digest):raise ValueError('Full model digest required')
    prompt_hash=hashlib.sha256(SYSTEM.encode()).hexdigest()
    if not args.run:
        print(json.dumps({'case_id':case['id'],'model':MODEL,'runtime':RUNTIME,'dataset_sha256':digest,'inference':False}));return
    with httpx.Client(base_url='http://127.0.0.1:11434',trust_env=False,follow_redirects=False,timeout=5) as client:
        version=client.get('/api/version');version.raise_for_status()
        tags=client.get('/api/tags');tags.raise_for_status()
        show=client.post('/api/show',json={'model':MODEL});show.raise_for_status()
        check_metadata(version.json(),tags.json(),show.json(),args.model_digest)
    folder=ROOT/'local/phase-6';folder.mkdir(parents=True,exist_ok=True)
    target=folder/f'local-v1-{args.model_digest[:12]}-{prompt_hash[:12]}-{case["id"]}.json'
    if target.exists():raise ValueError('Case output already reserved')
    lock=folder/'local-evaluation.active'
    settled=False
    with lock.open('x') as marker:marker.write(case['id'])
    try:
        with target.open('x',encoding='utf-8') as output:
            adapter=ModelAdapter(ModelProfile('ollama',MODEL,local_only=True,max_calls=1,ollama_think=False),capture_response=True)
            raw=trace=None;error=None
            try:
                response,trace=adapter.extract(case['sources'],case['context']);raw=response.model_dump(mode='json')
            except ProviderError as exc:error=str(exc)
            record={'case_id':case['id'],'model':MODEL,'model_digest':args.model_digest,'runtime_version':RUNTIME,'dataset_sha256':digest,
                    'prompt_sha256':prompt_hash,'schema_sha256':hashlib.sha256(json.dumps(wire_schema(),sort_keys=True).encode()).hexdigest(),
                    'code_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                    'profile':{'think':False,'num_ctx':4096,'num_predict':4096,'temperature':0,'keep_alive':0},
                    'response':raw,'trace':trace,'response_envelope':adapter.response_envelope,'score':score_extraction(case,raw,provider_error=error),
                    'scope':'Development only; real local API response if present. Semantic review remains required.'}
            if raw is not None:
                with TemporaryDirectory(prefix='sales-local-eval-') as tmp:record['pipeline']=exercise(case,raw,Path(tmp)/'core.sqlite')
            settled=adapter.response_envelope is not None
            record['runtime_observation_required']=not settled
            json.dump(record,output,indent=2)
        print(json.dumps({'case_id':case['id'],'score':record['score']}))
    finally:
        # A timeout can leave server inference running; require observation/owned
        # server stop before a human removes this marker. Never auto-retry.
        if settled:lock.unlink()


if __name__=='__main__':main()
