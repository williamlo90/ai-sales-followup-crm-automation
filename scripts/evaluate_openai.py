"""Explicit development pilot with one shared persistent USD1 ceiling."""
import argparse
import hashlib
import json
import math
import subprocess
from tempfile import TemporaryDirectory
from backend.evaluation_pipeline import exercise
from pathlib import Path
from backend.config import ROOT,read_config
from backend.providers import ModelAdapter,ModelProfile,ProviderError,SYSTEM,wire_schema
from backend.evaluation_budget import EvaluationBudget
from backend.evaluation_scoring import score_extraction

MODEL='gpt-4.1-mini-2025-04-14'
RUNNER_VERSION='evaluation-5-baseline-v3'
PRICE_SOURCE='https://developers.openai.com/api/docs/models/gpt-4.1-mini'
PRICE_CHECKED='2026-10-10'
PROFILES={
    'baseline': {'model':MODEL,'input_rate':0.4,'output_rate':1.6,'reasoning':None,'version':RUNNER_VERSION,'price_source':PRICE_SOURCE},
    'luna-low': {'model':'gpt-5.6-luna','input_rate':0.25,'output_rate':1.2,'reasoning':'low','version':'evaluation-5-luna-low-v3','price_source':'https://developers.openai.com/api/docs/models/gpt-5.6-luna'},
}



def run_case(case,adapter,budget,dataset_hash,profile_name="baseline"):
    profile=PROFILES[profile_name]
    model=profile['model']; input_rate=profile['input_rate']; output_rate=profile['output_rate']
    if adapter.profile.provider!='openai' or adapter.profile.model!=model or getattr(adapter.profile,'reasoning_effort',None)!=profile['reasoning']:raise ValueError('Unpriced profile')
    user=json.dumps({'sources':case['sources'],'context':case['context']},ensure_ascii=False)
    size=len((user+SYSTEM+json.dumps(wire_schema())).encode())
    if size>16000:raise ValueError('Evaluation input byte limit exceeded')
    # Byte-level upper estimate plus 8192 tokens of framing margin; reserve
    # full output allowance. No cached-input discount is assumed.
    reserved=math.ceil((size+8192)*input_rate+4096*output_rate)
    identity=json.dumps([dataset_hash,case['id'],model,SYSTEM,wire_schema(),RUNNER_VERSION if profile_name=='baseline' else profile],sort_keys=True)
    call_id=hashlib.sha256(identity.encode()).hexdigest()
    budget.reserve(call_id,json.dumps({'case_id':case['id'],'dataset_sha256':dataset_hash,'model':model}),reserved)
    raw=None;trace=None;error=None;actual=None
    try:
        result,trace=adapter.extract(case['sources'],case['context']);raw=result.model_dump(mode='json')
        usage=trace.get('usage',{})
        if all(type(usage.get(k)) is int and usage[k]>=0 for k in ['input_tokens','output_tokens']):
            actual=math.ceil(usage['input_tokens']*input_rate+usage['output_tokens']*output_rate)
    except ProviderError as exc:error=str(exc)
    except Exception:error='evaluation_internal_error'
    finally:
        envelope=getattr(adapter,'response_envelope',None)
        if actual is None and isinstance(envelope,dict):
            usage=envelope.get('usage',{})
            if all(type(usage.get(k)) is int and usage[k]>=0 for k in ['input_tokens','output_tokens']):
                actual=math.ceil(usage['input_tokens']*input_rate+usage['output_tokens']*output_rate)
        budget.finish(call_id,actual)
    return {'call_id':call_id,'dataset_sha256':dataset_hash,'case_id':case['id'],'model':model,
            'profile':profile,'price_source':profile['price_source'],'price_checked':PRICE_CHECKED,'reserved_microusd':reserved,
            'estimated_actual_microusd':actual,'response':raw,'trace':trace,'response_envelope':envelope,'runner_version':profile['version'],
            'score':score_extraction(case,raw,provider_error=error),'budget':budget.snapshot()}


def verify_profile_freeze(root,profile):
    freeze=json.loads((root/'docs/phase-6/openai-profile-freeze.json').read_text())
    checks=[freeze['profile']==profile,
            freeze['prompt_sha256']==hashlib.sha256(SYSTEM.encode()).hexdigest(),
            freeze['wire_schema_sha256']==hashlib.sha256(json.dumps(wire_schema(),sort_keys=True).encode()).hexdigest(),
            freeze['dataset_manifest_sha256']==hashlib.sha256((root/'docs/phase-6/dataset-freeze.json').read_bytes()).hexdigest()]
    if not all(checks):raise ValueError('Profile differs from held-out freeze')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--case',required=True);parser.add_argument('--run',action='store_true');parser.add_argument('--split',choices=['development','heldout'],default='development')
    parser.add_argument('--profile',choices=list(PROFILES),default='baseline')
    args=parser.parse_args()
    profile=PROFILES[args.profile];model=profile['model']
    if args.split=='heldout':verify_profile_freeze(ROOT,profile)
    path=ROOT/f'fixtures/evaluation/{args.split}-v2.json';data=path.read_bytes();doc=json.loads(data)
    manifest=json.loads((ROOT/'docs/phase-6/dataset-freeze.json').read_text())
    if hashlib.sha256(data).hexdigest()!=manifest['dataset_files'][path.relative_to(ROOT).as_posix()]:raise ValueError('Dataset differs from frozen labels')
    if hashlib.sha256((ROOT/'backend/evaluation_scoring.py').read_bytes()).hexdigest()!=manifest['scorer_sha256']:raise ValueError('Scorer differs from freeze')
    case=next(c for c in doc['cases'] if c['id']==args.case)
    digest=hashlib.sha256(data).hexdigest()
    if not args.run:
        print(json.dumps({'case_id':case['id'],'dataset_sha256':digest,'model':model,'paid_call':False}));return
    key=read_config()['OPENAI_API_KEY'].strip()
    if not key or any(c.isspace() for c in key):raise ValueError('Project OpenAI key missing or invalid')
    directory=ROOT/'local/phase-6';directory.mkdir(parents=True,exist_ok=True)
    target=directory/f"{profile['version']}-{digest[:16]}-{case['id']}.json"
    # Exclusive output reservation prevents silently replacing prior results.
    with target.open('x',encoding='utf-8') as output:
        record=run_case(case,ModelAdapter(ModelProfile('openai',model,key,max_calls=1,reasoning_effort=profile['reasoning']),capture_response=True),
            EvaluationBudget(directory/'budget.sqlite'),digest,args.profile)
        if record['response'] is not None:
            with TemporaryDirectory(prefix='sales-evaluation-core-') as temp:
                record['pipeline']=exercise(case,record['response'],Path(temp)/'core.sqlite')
        record['split']=doc['split']
        record['code_revision']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        record['prompt_sha256']=hashlib.sha256(SYSTEM.encode()).hexdigest()
        record['evaluation_scope']='frozen synthetic evaluation; semantic review and final quality acceptance remain separate'
        json.dump(record,output,indent=2)
    print(json.dumps({'case_id':case['id'],'score':record['score'],'budget':record['budget']}))


if __name__=='__main__':main()
