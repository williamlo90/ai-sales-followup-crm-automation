"""Frozen-case regression through real HTTP, PostgreSQL and budgeted OpenAI."""
import argparse
import hashlib
import json
import os
import secrets
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

import httpx
import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
from backend.config import ROOT
from backend.evaluation_budget import EvaluationBudget
from backend.evaluation_scoring import score_extraction, summarize
from scripts.evaluate_openai import PROFILES, verify_profile_freeze
from scripts.migrations import apply


def run(output):
    if os.environ.get('SALES_PHASE7_ACCEPTANCE')!='enabled':raise ValueError('Lab switch required')
    verify_profile_freeze(ROOT,PROFILES['luna-low'])
    dataset=ROOT/'fixtures/evaluation/heldout-v2.json'
    manifest=json.loads((ROOT/'docs/phase-6/dataset-freeze.json').read_text())
    digest=hashlib.sha256(dataset.read_bytes()).hexdigest()
    assert digest==manifest['dataset_files']['fixtures/evaluation/heldout-v2.json']
    assert hashlib.sha256((ROOT/'backend/evaluation_scoring.py').read_bytes()).hexdigest()==manifest['scorer_sha256']
    cases=json.loads(dataset.read_text())['cases']
    budget=EvaluationBudget(ROOT/'local/phase-6/budget.sqlite');before=budget.snapshot()
    assert before['remaining_microusd']>=230000 and before['pending']==0
    folder=ROOT/'local/phase-7'/('quality-'+uuid4().hex[:12]);folder.mkdir()
    schema='quality_'+uuid4().hex;password=secrets.token_urlsafe(32)
    identities={};tokens={};server=None;records=[]
    report={'status':'running','scope':'HTTP/native application + PostgreSQL + actual OpenAI; frozen regression set',
            'dataset_sha256':digest,'budget_before':before,'records':records}
    owner=psycopg.connect(os.environ['SALES_POSTGRES_DSN'],autocommit=True)
    try:
        assert owner.execute('SELECT current_database()').fetchone()[0]=='sales_phase7_acceptance'
        owner.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
        owner.execute(sql.SQL('SET search_path TO {}').format(sql.Identifier(schema)));apply(owner)
        owner.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOBYPASSRLS').format(sql.Identifier(schema),sql.Literal(password)))
        owner.execute(sql.SQL('GRANT USAGE ON SCHEMA {} TO {}').format(sql.Identifier(schema),sql.Identifier(schema)))
        owner.execute(sql.SQL('GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA {} TO {}').format(sql.Identifier(schema),sql.Identifier(schema)))
        for case in cases:
            tenant=str(uuid4());owner.execute('INSERT INTO tenants VALUES(%s,%s)',(tenant,case['id']))
            tokens[case['id']]={}
            for role in ('worker','operator'):
                actor=str(uuid4());token=secrets.token_urlsafe(32);tokens[case['id']][role]=token
                owner.execute('INSERT INTO actors(tenant_id,id,role) VALUES(%s,%s,%s)',(tenant,actor,role))
                identities[hashlib.sha256(token.encode()).hexdigest()]={'id':actor,'tenant_id':tenant,'role':role,
                    'deal_ids':list({d['id'] for d in case['linkage']['candidates']}|{case['context']['deal_id']})}
        identity=folder/'identities.json';identity.write_text(json.dumps(identities))
        runtime=make_conninfo(os.environ['SALES_POSTGRES_DSN'],user=schema,password=password,options=f'-c search_path={schema}')
        env=os.environ.copy();env.pop('SALES_CONNECTORS_PATH',None)
        env.update(SALES_STORAGE='postgresql',SALES_POSTGRES_DSN=runtime,SALES_IDENTITIES_PATH=str(identity),
                   SALES_MODEL_ENABLED='true',OPENAI_MODEL='gpt-5.6-luna',OPENAI_REASONING_EFFORT='low',
                   SALES_MODEL_CALL_LIMIT='10',SALES_MODEL_BUDGET_PATH='local/phase-6/budget.sqlite')
        with (folder/'runtime.log').open('w') as log, httpx.Client(base_url='http://127.0.0.1:8044',trust_env=False,timeout=75) as http:
            for index,case in enumerate(cases):
                if index%10==0:
                    if server:server.terminate();server.wait(timeout=10)
                    server=subprocess.Popen([sys.executable,'-m','uvicorn','backend.app:from_environment','--factory','--host','127.0.0.1','--port','8044','--no-access-log'],env=env,stdout=log,stderr=log)
                    for _ in range(50):
                        try:
                            if http.get('/health/ready').status_code==200:break
                        except httpx.HTTPError:pass
                        time.sleep(.25)
                    else:raise RuntimeError('Application readiness failed')
                def call(method,path,body=None,role='worker',params=None):
                    response=http.request(method,path,json=body,params=params,headers={'Authorization':'Bearer '+tokens[case['id']][role]})
                    if response.status_code not in (200,201):
                        raise RuntimeError('http_'+str(response.status_code))
                    return response.json()
                context=case['context'];deal=context['deal_id'];linkage=case['linkage']
                for candidate in linkage['candidates']:
                    call('PUT','/v1/ingest/deals/'+candidate['id'],{'account_id':candidate['account_id'],'title':context['title'],
                        'recipient':'evaluation-recipient@example.test','version':1,'deleted':candidate.get('deleted',False)})
                params={'account_id':linkage['account_id']}
                if linkage['explicit_deal_id']:params['deal_id']=linkage['explicit_deal_id']
                match=call('GET','/v1/deals/match',role='operator',params=params)
                record={'case_id':case['id'],'linkage_correct':match['status']==linkage['expected_status'] and match['deal_id']==linkage['expected_deal_id'],
                        'linkage':match,'proposals':[]}
                # Exercise abstention without spending a model call on unresolved linkage.
                if match['status']!='matched':
                    record.update(abstained=True,extraction_not_called='unresolved_linkage')
                else:
                    for commitment in context['commitment_history']:
                        evidence=commitment['evidence']
                        call('PUT',f'/v1/ingest/deals/{deal}/sources',{'external_id':evidence['source_id'],'revision':evidence['revision'],
                            'occurred_at':commitment['observed_at'],'text':evidence['quote']})
                        call('POST',f'/v1/deals/{deal}/commitments',commitment,role='operator')
                    for source in case['sources']:call('PUT',f'/v1/ingest/deals/{deal}/sources',source)
                    started=time.monotonic()
                    response=http.post('/v1/skills/extract_commitments',json={'deal_id':deal},headers={'Authorization':'Bearer '+tokens[case['id']]['operator']})
                    record['http_latency_seconds']=time.monotonic()-started
                    if response.status_code==200:
                        payload=response.json()['result'];raw=payload['extraction']
                        record.update(response=raw,trace=payload['trace'],score=score_extraction(case,raw))
                        record['abstained']=raw['status']!='ready'
                        if not record['abstained']:
                            for commitment in raw['commitments']:
                                call('POST',f'/v1/deals/{deal}/commitments',commitment,role='operator')
                                if commitment['state']=='cancelled':continue
                                proposal=call('POST','/v1/skills/prepare_crm_update',{'deal_id':deal,'deal_version':1,
                                    'commitment':{'id':commitment['id'],'revision':commitment['revision']}},role='operator')['result']
                                record['proposals'].append(proposal)
                    else:
                        record['score']=score_extraction(case,None,provider_error='http_'+str(response.status_code))
                records.append(record)
                (folder/'records.json').write_text(json.dumps(records,indent=2))
                (folder/'progress.json').write_text(json.dumps({'completed':len(records),'total':len(cases),'budget':budget.snapshot()}))
        report['operation_count']=owner.execute('SELECT count(*) FROM operations').fetchone()[0]
        report['approval_count']=owner.execute('SELECT count(*) FROM approvals').fetchone()[0]
        assert report['operation_count']==report['approval_count']==0
        eligible=[c for c in cases if c['linkage']['expected_status']=='matched']
        report['extraction_summary']=summarize(eligible,[r['score'] for r in records if 'score' in r])
        report['linkage_correct']=sum(r['linkage_correct'] for r in records)
        report['status']='completed_pending_semantic_review'
    except Exception as error:
        report.update(status='failed',error_type=type(error).__name__,completed_cases=len(records))
    finally:
        if server and server.poll() is None:server.terminate();server.wait(timeout=10)
        owner.close()
        report['budget_after']=budget.snapshot()
        output.write_text(json.dumps(report,indent=2));(folder/'result.json').write_text(json.dumps(report,indent=2))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists():raise SystemExit('Output already exists')
    result=run(args.output)
    print(json.dumps({'status':result['status'],'completed_cases':len(result['records'])}))
    raise SystemExit(0 if result['status']=='completed_pending_semantic_review' else 1)
