import hashlib,json,os,secrets,subprocess,sys,time,traceback
import _thread,threading
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4
import httpx,psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
from backend.config import ROOT
from backend.domain import canonical
from backend.models import Actor
from backend.connector_runtime import ConnectorConfig, graph_token_reader
from backend.graph_effects import GraphMailAdapter
from backend.read_clients import BoundedReader
from scripts.migrations import apply
from scripts.export_workflows import workflow

if os.environ.get('SALES_PHASE7_ACCEPTANCE')!='enabled':raise SystemExit('Explicit Phase7 lab switch required')
folder=Path(os.environ['SALES_CONNECTED_FOLDER']);cfg=json.loads((folder/'session.json').read_text())
outlook_send=os.environ.get('SALES_CONNECTED_OUTLOOK_SEND')=='enabled'
recipient=None
permit=None
if outlook_send:
 if not (folder/'selected-message.json').is_file():raise SystemExit('Selected synthetic message required')
 if (folder/'send-attempt.json').exists() or (folder/'send-operation.json').exists():raise SystemExit('Send already attempted; observe only')
 permit=json.loads((folder/'send-authorization.json').read_text(encoding='utf-8'))
 if permit.get('maximum_sends')!=1 or permit.get('sent') is not False:raise SystemExit('One-send authorization required')
 recipient=permit.get('recipient')
 prior=json.loads((ROOT/'local/graph-ingestion/send-authorization.json').read_text(encoding='utf-8'))
 if not isinstance(recipient,str) or recipient!=prior.get('recipient') or prior.get('sent') is not True:
  raise SystemExit('Established self-test Outlook recipient required')
 private_cfg=ConnectorConfig.model_validate(json.loads((ROOT/'local/connectors.json').read_text(encoding='utf-8')))
 if not private_cfg.graph or not private_cfg.graph.oauth:raise SystemExit('Project Outlook OAuth required')
 selected_test=json.loads((folder/'selected-message.json').read_text(encoding='utf-8'))
 if selected_test.get('subject')!='Sales OAuth end-to-end 12 Okt':raise SystemExit('Wrong synthetic message')
 token_reader=graph_token_reader(private_cfg.graph)
 reader=BoundedReader(token_reader)
 mail_url='https://graph.microsoft.com/v1.0/users/'+quote(private_cfg.graph.mailbox,safe='')+'/messages/'+quote(selected_test['id'],safe='')
 source_message=reader.get(mail_url+'?$select=id,subject,body,from,receivedDateTime',
                           {'Prefer':'outlook.body-content-type="text", IdType="ImmutableId"'})
 source_text=source_message.get('body',{}).get('content','')
 if (source_message.get('id')!=selected_test['id'] or source_message.get('subject')!=selected_test['subject']
     or not isinstance(source_text,str) or 'Tolong tindak lanjuti proposal Northstar 25 seat' not in source_text
     or '12 Oktober 2026 pukul 18.00 WIB' not in source_text):
  raise SystemExit('Synthetic source content mismatch')
name='sales04-connected-'+uuid4().hex[:12];(folder/'engine-name.txt').write_text(name)
actors={};tokens={};server=None;engine=None
report={'status':'running','scope':'simultaneous real Graph/OpenAI/n8n/API/PostgreSQL/Odoo; automated lab review roles'}
abort_monitor_stop=threading.Event()
def watch_abort():
 while not abort_monitor_stop.wait(.25):
  if (folder/'abort.flag').exists():
   _thread.interrupt_main()
   return
threading.Thread(target=watch_abort,daemon=True).start()
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
 selected=json.loads(((folder if outlook_send else ROOT/'local/graph-ingestion')/'selected-message.json').read_text())
 graph=json.loads((ROOT/'local/connectors.json').read_text())['graph'];graph['message_deals']={selected['id']:'connected-demo'}
 (folder/'odoo-token').write_text(cfg['operator_token'])
 connector={'local_tenant':tenant,'worker_id':actors['worker'].id,'crm_write_enabled':True,
            'email_send_enabled':outlook_send,'email_recipient_allowlist':[recipient] if outlook_send else [],
            'graph':graph,'odoo':{'base_url':cfg['base_url'],'connector_tenant':cfg['tenant'],'company_id':cfg['company_id'],'token_file':str(folder/'odoo-token'),'deals':{'connected-demo':{'opportunity_id':cfg['opportunity_id'],'assignee_id':cfg['assignee_id']}}}}
 (folder/'connectors.json').write_text(json.dumps(connector))
 env=os.environ.copy();env.update(SALES_STORAGE='postgresql',SALES_POSTGRES_DSN=runtime,SALES_IDENTITIES_PATH=str(folder/'identities.json'),SALES_CONNECTORS_PATH=str(folder/'connectors.json'),SALES_MODEL_ENABLED='true',OPENAI_MODEL='gpt-5.6-luna',OPENAI_REASONING_EFFORT='low',SALES_MODEL_CALL_LIMIT='1',SALES_MODEL_BUDGET_PATH='local/phase-6/budget.sqlite',SALES_LAB_EXTRACTION_OUTPUT=str(folder/'extraction.json'))
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
  call(h,'PUT','/v1/ingest/deals/connected-demo',body={'account_id':'Northstar','title':'Synthetic Northstar follow-up' if outlook_send else 'Synthetic Northstar demo','recipient':recipient if outlook_send else 'buyer@example.test','version':1})
  docs=[]
  for journey in ('intake','due'):
   doc=workflow(journey);doc['settings']['saveDataSuccessExecution']='all'
   for node in doc['nodes']:
    if node['type'].endswith('scheduleTrigger'):node['parameters']={'rule':{'interval':[{'field':'seconds','secondsInterval':10}]}}
    if node['type'].endswith('httpRequest'):
     node['parameters']['url']=node['parameters']['url'].replace('sales-domain:8040','host.docker.internal:8044');node['credentials']['httpHeaderAuth']['id']='connected-worker'
   docs.append(doc)
  def httpnode(name,path,body=None):
   p={'method':'POST','url':'http://host.docker.internal:8044'+path,'authentication':'genericCredentialType','genericAuthType':'httpHeaderAuth','options':{'timeout':65000}}
   if body is not None:p.update(sendBody=True,specifyBody='json',jsonBody=json.dumps(body))
   return {'id':uuid4().hex,'name':name,'type':'n8n-nodes-base.httpRequest','typeVersion':4.5,'position':[240,0],'parameters':p,'credentials':{'httpHeaderAuth':{'id':'connected-worker','name':'Sales scoped worker'}},'retryOnFail':False}
  graph_node=('Graph selected' if outlook_send else 'Graph poll')
  graph_path=('/v1/ingest/graph/selected' if outlook_send else '/v1/ingest/graph/poll')
  graph_body=({'id':selected['id']} if outlook_send else None)
  entry={'id':'connected-ingestion','name':'Connected ingestion lab','active':False,
         'nodes':[{'id':uuid4().hex,'name':'Start','type':'n8n-nodes-base.executeWorkflowTrigger','typeVersion':1,'position':[0,0],'parameters':{}},
                  httpnode(graph_node,graph_path,graph_body),httpnode('Extract','/v1/skills/extract_commitments',{'deal_id':'connected-demo'})],
         'connections':{'Start':{'main':[[{'node':graph_node,'type':'main','index':0}]]},
                        graph_node:{'main':[[{'node':'Extract','type':'main','index':0}]]}},
         'settings':{'executionOrder':'v1','saveDataSuccessExecution':'all'}}
  (folder/'workflows.json').write_text(json.dumps(docs+[entry]));(folder/'credentials.json').write_text(json.dumps([{'id':'connected-worker','name':'Sales scoped worker','type':'httpHeaderAuth','data':{'name':'Authorization','value':'Bearer '+tokens['worker']}}]))
  command='n8n import:credentials --input=/lab/credentials.json && n8n import:workflow --input=/lab/workflows.json && n8n execute --id=connected-ingestion && '+' && '.join('n8n publish:workflow --id='+d['id'] for d in docs)+' && exec n8n start'
  engine=subprocess.Popen(['docker','run','--pull','never','--name',name,'--label','sales.phase7.owner=connected-lab','--memory','512m','--memory-swap','512m','--cpus','0.5','--pids-limit','96','-e','NODE_OPTIONS=--max-old-space-size=320','-e','N8N_DIAGNOSTICS_ENABLED=false','-e','N8N_VERSION_NOTIFICATIONS_ENABLED=false','--mount',f'type=volume,source={name}-data,target=/home/node/.n8n','--mount',f'type=bind,source={folder},target=/lab,readonly','--entrypoint','/bin/sh','sha256:673cf422821d5dda078bda7962e5c48be400745a843041618a2ad2263972a3b9','-c',command],stdout=log,stderr=log)
  checkpoint('n8n_graph_model')
  for _ in range(100):
   if (folder/'extraction.json').exists():break
   if engine.poll() is not None:raise RuntimeError('engine_exited')
   time.sleep(1)
  else:raise RuntimeError('extraction_deadline')
  extracted=json.loads((folder/'extraction.json').read_text())
  if 'result' not in extracted:raise RuntimeError('extraction_failed_'+str(extracted.get('error','unknown')))
  result=extracted['result'];extraction=result['extraction']
  report['model_status']=extraction['status'];report['model_trace']=result['trace']
  commitments=extraction['commitments']
  if outlook_send and not commitments:
   # An internal owner was absent from the customer mail. Lab review explicitly
   # supplies one; it never presents this as a model-extracted commitment.
   missing=extraction.get('missing_information',[])
   if (extraction['status']!='review' or extraction.get('conflicts')
       or len(missing)!=1 or 'owner' not in missing[0].lower()):
    raise RuntimeError('model_requires_other_missing_facts')
   quote='Tolong tindak lanjuti proposal Northstar 25 seat dan kirim ringkasan harga hari ini, 12 Oktober 2026 pukul 18.00 WIB.'
   if quote not in source_text:raise RuntimeError('synthetic_evidence_mismatch')
   source_id='graph:'+hashlib.sha256(canonical([graph['mailbox'],selected['id']]).encode()).hexdigest()
   commitment={'id':'northstar-synthetic-pricing-request','revision':1,'supersedes':None,
               'owner':'Sales lab operator',
               'description':'Acknowledge synthetic Northstar 25-seat pricing request and confirm the next step without an unverified price',
               'due_at':'2026-10-12T18:00:00+07:00','observed_at':source_message['receivedDateTime'],
               'evidence':{'source_id':source_id,'revision':1,'quote':quote},'state':'active'}
   report['review_resolution']='lab operator supplied missing internal owner; no price invented'
  else:
   if not commitments:raise RuntimeError('model_requires_missing_facts')
   # The old test accepts the dated demo; the Outlook test accepts only one due item.
   choices=([c for c in commitments if datetime.fromisoformat(c['due_at'])<=datetime.now(timezone.utc)]
            if outlook_send else [c for c in commitments if '2026-10-15T' in c['due_at'] and 'demo' in c['description'].lower()])
   assert len(choices)==1
   commitment=choices[0]
  call(h,'POST','/v1/deals/connected-demo/commitments',role='operator',body=commitment)
  job=call(h,'POST','/v1/workflows/jobs',body={'deal_id':'connected-demo','deal_version':1,'journey':'intake','kind':'crm','commitment':{'id':commitment['id'],'revision':commitment['revision']}},status=201)
  checkpoint('awaiting_n8n_proposal')
  for _ in range(80):
   job=call(h,'GET','/v1/workflows/jobs/'+job['id'])
   if job['proposal_id']:break
   time.sleep(1)
  else:raise RuntimeError('proposal_deadline')
  proposal=call(h,'GET','/v1/proposals/'+job['proposal_id'],role='operator')
  preview=call(h,'GET','/v1/proposals/'+proposal['id']+'/connector-preparation',role='operator')['preview']
  with httpx.Client(base_url=cfg['base_url'],trust_env=False,timeout=25) as remote:
   r=remote.post('/v1/activities/prepare',headers={'Authorization':'Bearer '+cfg['operator_token']},json={k:preview[k] for k in ('opportunity_id','assignee_id','due_date','summary')});assert r.status_code==201;prepared=r.json()
   r=remote.post('/v1/proposals/'+prepared['id']+'/approve',headers={'Authorization':'Bearer '+cfg['approver_token']},json={'payload_hash':prepared['payload_hash']});assert r.status_code==201;approval=r.json()
  call(h,'POST','/v1/proposals/'+proposal['id']+'/connector-binding',role='operator',body={'connector_tenant':cfg['tenant'],'proposal_id':prepared['id'],'approval_id':approval['id'],'actor_id':prepared['actor_id'],'preview':prepared['preview']})
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
  if outlook_send:
   payload=proposal['payload']
   if payload['recipient']!=recipient or not payload['draft'] or not payload['summary']:
    raise RuntimeError('email_review_mismatch')
   due=call(h,'GET','/v1/proposals/'+proposal['id']+'/eligibility?kind=email',role='operator')
   if due.get('reason') not in {'approval_required','due_and_approved'}:raise RuntimeError('email_not_due')
   due_jobs=[j for j in call(h,'GET','/v1/workflows/jobs')['items']
             if j['journey']=='due' and j['proposal_id']==proposal['id']]
   if len(due_jobs)!=1:raise RuntimeError('automatic_due_email_job_required')
   email_job=due_jobs[0]
   intent={'recipient':recipient,'subject':payload['summary'],'body':payload['draft'],
           'proposal_id':proposal['id'],'payload_hash':proposal['payload_hash']}
   with (folder/'send-intent.json').open('x',encoding='utf-8') as out:json.dump(intent,out)
   # Reserve the one allowed attempt before approval makes the scheduled worker eligible.
   with (folder/'send-attempt.json').open('x',encoding='utf-8') as out:
    json.dump({'reserved_at':datetime.now(timezone.utc).isoformat(),'proposal_id':proposal['id'],'maximum_attempts':1},out)
   checkpoint('email_attempt_reserved')
   call(h,'POST','/v1/proposals/'+proposal['id']+'/approvals',role='approver',body={'kind':'email','payload_hash':proposal['payload_hash']})
   checkpoint('awaiting_n8n_email_effect')
   for _ in range(120):
    email_job=call(h,'GET','/v1/workflows/jobs/'+email_job['id'])
    if email_job['status']=='completed':break
    if email_job['status'] in {'review','unknown','disabled'}:raise RuntimeError('email_workflow_'+email_job['status'])
    time.sleep(1)
   else:raise RuntimeError('email_effect_deadline')
   email_operation=call(h,'GET','/v1/operations/'+email_job['operation_id'])
   with (folder/'send-operation.json').open('x',encoding='utf-8') as out:json.dump(email_operation,out)
   if email_operation['status']!='accepted':raise RuntimeError('email_not_accepted')
   permit['sent']=True;permit['attempt_reserved']=True
   (folder/'send-authorization.json').write_text(json.dumps(permit,indent=2),encoding='utf-8')
   adapter=GraphMailAdapter(tenant,graph['mailbox'],graph_token_reader(private_cfg.graph),lambda t,p:payload,
                            recipients=frozenset({recipient}),send_enabled=False)
   sent_items=False
   for _ in range(30):
    try:receipt=adapter.observe({'tenant':tenant,**email_operation})
    except Exception:receipt=None
    if receipt and receipt['state']=='sent':sent_items=True;break
    time.sleep(2)
   if not sent_items:raise RuntimeError('sent_items_not_verified')
   operations=call(h,'GET','/v1/proposals/'+proposal['id']+'/operations')['items'];assert len(operations)==2
   report.update(status='passed',job_status=job['status'],operation_status=operation['status'],
                 operation_count=2,emails_sent=1,email_job_status=email_job['status'],
                 email_operation_status=email_operation['status'],sent_items_verified=True,
                 review='automated distinct lab approver, exact payload; one self-test Outlook send')
  else:
   report.update(status='passed',job_status=job['status'],operation_status=operation['status'],operation_count=1,emails_sent=0,review='automated lab reviewer selects supported demo; separate approver approves exact payload')
except KeyboardInterrupt:
 report.update(status='interrupted',error_type='SupervisorOrUserAbort')
except Exception as error:
 report.update(status='failed',error_type=type(error).__name__,location=[f'{Path(f.filename).name}:{f.lineno}' for f in traceback.extract_tb(error.__traceback__)[-3:]])
finally:
 abort_monitor_stop.set()
 subprocess.run(['docker','stop','--time','5',name],capture_output=True,timeout=25)
 if engine and engine.poll() is None:engine.wait(timeout=10)
 if server and server.poll() is None:
  if os.name=='nt':subprocess.run(['taskkill','/PID',str(server.pid),'/T','/F'],capture_output=True,timeout=15)
  else:server.terminate()
  server.wait(timeout=10)
 (folder/'probe.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))

sys.exit(0 if report["status"]=="passed" else 1)
