import hashlib,json,os,secrets,subprocess,sys,time,traceback
from pathlib import Path
from uuid import uuid4
import httpx,psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
from backend.config import ROOT
from backend.models import Actor
from scripts.migrations import apply
from scripts.export_workflows import workflow

if os.environ.get('SALES_PHASE7_ACCEPTANCE')!='enabled':raise SystemExit('Explicit Phase7 lab switch required')
folder=Path(os.environ['SALES_CONNECTED_FOLDER']);cfg=json.loads((folder/'session.json').read_text())
name='sales04-connected-'+uuid4().hex[:12];(folder/'engine-name.txt').write_text(name)
actors={};tokens={};server=None;engine=None
report={'status':'running','scope':'simultaneous real Graph/OpenAI/n8n/API/PostgreSQL/Odoo; automated lab review roles'}
def checkpoint(stage):
 report['stage']=stage;(folder/'progress.json').write_text(json.dumps(report))
def call(http,method,path,role='worker',body=None,status=200):
 r=http.request(method,path,headers={'Authorization':'Bearer '+tokens[role]},json=body)
 if r.status_code!=status:
  (folder/'private-http-error.json').write_text(json.dumps({'path':path,'status':r.status_code,'body':r.text}))
  raise RuntimeError('http_status')
 return r.json()
try:
 checkpoint('resume_saved_proposal')
 candidates=[]
 for candidate in (ROOT/'local/phase-7/sales04-odoo-20261010142205').glob('connected-*'):
  if (candidate/'probe.json').exists():
   previous=json.loads((candidate/'probe.json').read_text())
   if previous.get('stage')=='awaiting_n8n_proposal' and (candidate/'private-http-error.json').exists():candidates.append(candidate)
 assert len(candidates)==1
 prior=candidates[0];state=json.loads((prior/'private-runtime.json').read_text())
 tokens=state['tokens'];runtime=state['runtime_dsn']
 (prior/'odoo-token').write_text(cfg['operator_token'])
 report['resumes_prior_graph_model_pipeline']=True
 report['paid_calls_this_resume']=0
 env=os.environ.copy();env.update(SALES_STORAGE='postgresql',SALES_POSTGRES_DSN=runtime,SALES_IDENTITIES_PATH=str(prior/'identities.json'),SALES_CONNECTORS_PATH=str(prior/'connectors.json'),SALES_MODEL_ENABLED='false',SALES_LAB_EXTRACTION_OUTPUT=str(folder/'unused-extraction.json'))
 log=(folder/'runtime.log').open('w')
 server=subprocess.Popen([sys.executable,'-m','uvicorn','scripts.connected_lab_app:factory','--factory','--host','127.0.0.1','--port','8044','--no-access-log'],env=env,stdout=log,stderr=log)
 old_engine=(prior/'engine-name.txt').read_text()
 engine=subprocess.Popen(['docker','run','--pull','never','--name',name,'--label','sales.phase7.owner=connected-lab','--memory','512m','--memory-swap','512m','--cpus','0.5','--pids-limit','96','-e','NODE_OPTIONS=--max-old-space-size=320','-e','N8N_DIAGNOSTICS_ENABLED=false','-e','N8N_VERSION_NOTIFICATIONS_ENABLED=false','--mount',f'type=volume,source={old_engine}-data,target=/home/node/.n8n','--entrypoint','/bin/sh','sha256:673cf422821d5dda078bda7962e5c48be400745a843041618a2ad2263972a3b9','-c','exec n8n start'],stdout=log,stderr=log)
 with httpx.Client(base_url='http://127.0.0.1:8044',trust_env=False,timeout=65) as h:
  for _ in range(50):
   try:
    if h.get('/health/ready').status_code==200:break
   except httpx.HTTPError:pass
   time.sleep(.25)
  else:raise RuntimeError('app_readiness')
  jobs=call(h,'GET','/v1/workflows/jobs')['items'];assert len(jobs)==1;job=jobs[0]
  proposal=call(h,'GET','/v1/proposals/'+job['proposal_id'],role='operator')
  preview=call(h,'GET','/v1/proposals/'+proposal['id']+'/connector-preparation',role='operator')['preview']
  with httpx.Client(base_url=cfg['base_url'],trust_env=False,timeout=25) as remote:
   r=remote.post('/v1/activities/prepare',headers={'Authorization':'Bearer '+cfg['operator_token']},json={k:preview[k] for k in ('opportunity_id','assignee_id','due_date','summary')});assert r.status_code==201;prepared=r.json()
   r=remote.post('/v1/proposals/'+prepared['id']+'/approve',headers={'Authorization':'Bearer '+cfg['approver_token']},json={'payload_hash':prepared['payload_hash']});assert r.status_code==201;approval=r.json()
  call(h,'POST','/v1/proposals/'+proposal['id']+'/connector-binding',role='worker',body={'connector_tenant':cfg['tenant'],'proposal_id':prepared['id'],'approval_id':approval['id'],'actor_id':prepared['actor_id'],'preview':prepared['preview']})
  call(h,'POST','/v1/proposals/'+proposal['id']+'/approvals',role='approver',body={'kind':'crm','payload_hash':proposal['payload_hash']})
  checkpoint('awaiting_n8n_effect')
  for _ in range(120):
   job=call(h,'GET','/v1/workflows/jobs/'+job['id'])
   if job['status']=='completed':break
   if job['status']=='review':raise RuntimeError('workflow_review')
   time.sleep(1)
  else:raise RuntimeError('effect_deadline')
  operation=call(h,'GET','/v1/operations/'+job['operation_id']);assert operation['status']=='verified'
  operations=call(h,'GET','/v1/proposals/'+proposal['id']+'/operations')['items'];assert len(operations)==1
  report.update(status='passed',job_status=job['status'],operation_status=operation['status'],operation_count=1,emails_sent=0,review='automated lab reviewer selects supported demo; separate approver approves exact payload')
except Exception as error:
 report.update(status='failed',error_type=type(error).__name__,location=[f'{Path(f.filename).name}:{f.lineno}' for f in traceback.extract_tb(error.__traceback__)[-3:]])
finally:
 subprocess.run(['docker','stop','--time','5',name],capture_output=True,timeout=25)
 if engine and engine.poll() is None:engine.wait(timeout=10)
 if server and server.poll() is None:server.terminate();server.wait(timeout=10)
 (folder/'probe.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))

sys.exit(0 if report["status"]=="passed" else 1)
