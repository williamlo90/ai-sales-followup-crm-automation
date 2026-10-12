import hashlib,json,os,secrets,subprocess,sys,time,traceback
import _thread,threading
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
report={'status':'running','scope':'Real n8n/API/PostgreSQL/Odoo workload; deterministic seeded input, model disabled; automated lab review'}
abort_monitor_stop=threading.Event()
def watch_abort():
 while not abort_monitor_stop.wait(.25):
  if (folder/'abort.flag').exists():
   _thread.interrupt_main()
   return
if os.name=='nt':threading.Thread(target=watch_abort,daemon=True).start()
def checkpoint(stage):
 report['stage']=stage;(folder/'progress.json').write_text(json.dumps(report))
def call(http,method,path,role='worker',body=None,status=200):
 r=http.request(method,path,headers={'Authorization':'Bearer '+tokens[role]},json=body)
 if r.status_code!=status:
  (folder/'private-http-error.json').write_text(json.dumps({'path':path,'status':r.status_code,'body':r.text}))
  raise RuntimeError('http_status')
 return r.json()
try:
 checkpoint('database_setup')
 schema='sales_connected_'+uuid4().hex;password=secrets.token_urlsafe(32);tenant=str(uuid4())
 with psycopg.connect(os.environ['SALES_POSTGRES_DSN'],autocommit=True) as owner:
  assert owner.execute('SELECT current_database()').fetchone()[0]=='sales_phase7_acceptance'
  owner.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)));owner.execute(sql.SQL('SET search_path TO {}').format(sql.Identifier(schema)));apply(owner)
  owner.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOBYPASSRLS').format(sql.Identifier(schema),sql.Literal(password)))
  owner.execute(sql.SQL('GRANT USAGE ON SCHEMA {} TO {}').format(sql.Identifier(schema),sql.Identifier(schema)))
  owner.execute(sql.SQL('GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA {} TO {}').format(sql.Identifier(schema),sql.Identifier(schema)))
  owner.execute('INSERT INTO tenants VALUES(%s,%s)',(tenant,'connected-lab'))
  for role in ('worker','operator','approver'):
   actors[role]=Actor(id=str(uuid4()),tenant_id=tenant,role=role,deal_ids={'connected-demo'});tokens[role]=secrets.token_urlsafe(32)
   owner.execute('INSERT INTO actors(tenant_id,id,role) VALUES(%s,%s,%s)',(tenant,actors[role].id,role))
 runtime=make_conninfo(os.environ['SALES_POSTGRES_DSN'],user=schema,password=password,options=f'-c search_path={schema}')
 (folder/'identities.json').write_text(json.dumps({hashlib.sha256(tokens[r].encode()).hexdigest():a.model_dump(mode='json') for r,a in actors.items()}))
 (folder/'odoo-token').write_text(cfg['operator_token'])
 connector={'local_tenant':tenant,'worker_id':actors['worker'].id,'crm_write_enabled':True,'odoo':{'base_url':cfg['base_url'],'connector_tenant':cfg['tenant'],'company_id':cfg['company_id'],'token_file':str(folder/'odoo-token'),'deals':{'connected-demo':{'opportunity_id':cfg['opportunity_id'],'assignee_id':cfg['assignee_id']}}}}
 (folder/'connectors.json').write_text(json.dumps(connector))
 env=os.environ.copy();env.update(SALES_STORAGE='postgresql',SALES_POSTGRES_DSN=runtime,SALES_IDENTITIES_PATH=str(folder/'identities.json'),SALES_CONNECTORS_PATH=str(folder/'connectors.json'),SALES_MODEL_ENABLED='false',OPENAI_MODEL='gpt-5.6-luna',OPENAI_REASONING_EFFORT='low',SALES_MODEL_CALL_LIMIT='1',SALES_MODEL_BUDGET_PATH='local/phase-6/budget.sqlite',SALES_LAB_EXTRACTION_OUTPUT=str(folder/'extraction.json'))
 (folder/'private-runtime.json').write_text(json.dumps({'runtime_dsn':runtime,'actors':{r:a.model_dump(mode='json') for r,a in actors.items()},'tokens':tokens}))
 log=(folder/'runtime.log').open('w')
 server=subprocess.Popen([sys.executable,'-m','uvicorn','scripts.connected_lab_app:factory','--factory','--host','127.0.0.1','--port','8044','--no-access-log'],env=env,stdout=log,stderr=log)
 with httpx.Client(base_url='http://127.0.0.1:8044',trust_env=False,timeout=65) as h:
  for _ in range(50):
   try:
    if h.get('/health/ready').status_code==200:break
   except httpx.HTTPError:pass
   time.sleep(.25)
  else:raise RuntimeError('app_readiness')
  call(h,'PUT','/v1/ingest/deals/connected-demo',body={'account_id':'Northstar','title':'Synthetic Northstar demo','recipient':'buyer@example.test','version':1})
  docs=[]
  for journey in ('intake','due'):
   doc=workflow(journey);doc['settings']['saveDataSuccessExecution']='all'
   for node in doc['nodes']:
    if node['type'].endswith('scheduleTrigger'):node['parameters']={'rule':{'interval':[{'field':'seconds','secondsInterval':10}]}}
    if node['type'].endswith('httpRequest'):
     node['parameters']['url']=node['parameters']['url'].replace('sales-domain:8040','host.docker.internal:8044');node['credentials']['httpHeaderAuth']['id']='connected-worker'
   docs.append(doc)
  (folder/'workflows.json').write_text(json.dumps(docs));(folder/'credentials.json').write_text(json.dumps([{'id':'connected-worker','name':'Sales scoped worker','type':'httpHeaderAuth','data':{'name':'Authorization','value':'Bearer '+tokens['worker']}}]))
  from scripts.n8n_lab_bootstrap import command as bootstrap_command
  command=bootstrap_command([d['id'] for d in docs])
  engine=subprocess.Popen(['docker','run','--pull','never','--name',name,'--label','sales.phase7.owner=connected-lab','--memory','512m','--memory-swap','512m','--cpus','0.5','--pids-limit','96','-e','NODE_OPTIONS=--max-old-space-size=320','-e','N8N_DIAGNOSTICS_ENABLED=false','-e','N8N_VERSION_NOTIFICATIONS_ENABLED=false','--mount',f'type=volume,source={name}-data,target=/home/node/.n8n','--mount',f'type=bind,source={folder},target=/lab,readonly','--entrypoint','/bin/sh','sha256:673cf422821d5dda078bda7962e5c48be400745a843041618a2ad2263972a3b9','-c',command],stdout=log,stderr=log)
  if os.environ.get('SALES_MISSED_SCHEDULE_PROBE')=='enabled':
   from scripts.n8n_missed_schedule import run
  else:
   from scripts.connected_workload_steps import run
  report.update(run(h,call,cfg,folder))
except KeyboardInterrupt:
 report.update(status='interrupted',error_type='SupervisorOrUserAbort')
except Exception as error:
 report.update(status='failed',error_type=type(error).__name__,location=[f'{Path(f.filename).name}:{f.lineno}' for f in traceback.extract_tb(error.__traceback__)[-3:]])
finally:
 abort_monitor_stop.set()
 (folder/'probe.json').write_text(json.dumps(report,indent=2))
 if server and server.poll() is None:
  if os.name=='nt':subprocess.run(['taskkill','/PID',str(server.pid),'/T','/F'],capture_output=True,timeout=15)
  else:server.terminate()
  server.wait(timeout=10)
 # docker run may still be creating its container when early input validation fails.
 for _ in range(30):
  found=subprocess.run(['docker','inspect','--format','{{.Id}}',name],capture_output=True,timeout=5)
  if found.returncode==0 or not engine or engine.poll() is not None:break
  time.sleep(1)
 subprocess.run(['docker','stop','--time','5',name],capture_output=True,timeout=25)
 if engine and engine.poll() is None:
  try:engine.wait(timeout=10)
  except subprocess.TimeoutExpired:engine.terminate();engine.wait(timeout=10)
 (folder/'probe.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))

sys.exit(0 if report["status"]=="passed" else 1)
