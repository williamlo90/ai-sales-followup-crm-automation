"""Actual n8n CLI workflow execution against native HTTP + real PostgreSQL."""
import hashlib
import json
import os
import secrets
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import httpx
from backend.config import ROOT
from backend.domain import SalesService
from backend.models import Actor, DealInput, SourceInput
from backend.postgres_store import PostgresStore
from backend.sales_rules import Commitment
from backend.skills import SkillService
from backend.workflows import WorkflowService, EnqueueInput


def check_n8n(owner, dsn, tenant):
    normal=os.environ.get('SALES_N8N_NORMAL_CADENCE')=='enabled'
    scheduled=os.environ.get('SALES_N8N_SCHEDULE_PROBE')=='enabled'
    name='sales04-n8n-execute-'+uuid4().hex[:12]
    folder=ROOT/'local/phase-7'/name;folder.mkdir()
    worker=Actor(id=str(uuid4()),tenant_id=str(tenant),role='worker',deal_ids={'engine-deal'})
    owner.execute('INSERT INTO actors(tenant_id,id,role) VALUES(%s,%s,%s)',(tenant,worker.id,'worker'))
    token=secrets.token_urlsafe(32)
    identity=folder/'identities.json'
    identity.write_text(json.dumps({hashlib.sha256(token.encode()).hexdigest():worker.model_dump(mode='json')}))
    sales=SalesService(PostgresStore(dsn));now=datetime.now(timezone.utc)
    sales.put_deal(worker,'engine-deal',DealInput(account_id='engine-lab',title='Engine test',recipient='buyer@example.test',version=1))
    sales.put_source(worker,'engine-deal',SourceInput(external_id='engine-source',revision=1,occurred_at=now,text='Please confirm the synthetic demo.'))
    sales.commitment(worker,'engine-deal',Commitment(id='engine-commitment',revision=1,owner='Sales',description='Confirm synthetic demo',due_at=now+timedelta(days=1),observed_at=now,evidence={'source_id':'engine-source','revision':1,'quote':'Please confirm the synthetic demo.'}))
    workflow=WorkflowService(sales,SkillService(sales))
    job=workflow.enqueue(worker,EnqueueInput(deal_id='engine-deal',deal_version=1,journey='intake',kind='crm',commitment={'id':'engine-commitment','revision':1}))
    creds=[{'id':'sales-worker-lab','name':'Sales scoped worker','type':'httpHeaderAuth','data':{'name':'Authorization','value':'Bearer '+token}}]
    (folder/'credentials.json').write_text(json.dumps(creds))
    ids=[]; documents=[]
    for journey in ('intake','due'):
        data=json.loads((ROOT/f'automation/n8n/{journey}-v1.json').read_text())
        for node in data['nodes']:
            if node['type']=='n8n-nodes-base.scheduleTrigger':
                # CLI needs an Execute Workflow Trigger. Preserve production
                # schedule exports; this probe does not establish scheduling.
                if scheduled and not normal:node['parameters']={'rule':{'interval':[{'field':'seconds','secondsInterval':10}]}}
                elif not scheduled:node.update(type='n8n-nodes-base.executeWorkflowTrigger',typeVersion=1,parameters={})
            if node['type']=='n8n-nodes-base.httpRequest':
                node['parameters']['url']=node['parameters']['url'].replace('sales-domain:8040','host.docker.internal:8044')
                node['credentials']['httpHeaderAuth']['id']='sales-worker-lab'
        if scheduled:data['settings']['saveDataSuccessExecution']='all'
        ids.append(data['id']);documents.append(data)
    (folder/'workflows.json').write_text(json.dumps(documents))
    env=os.environ.copy();env.update(SALES_STORAGE='postgresql',SALES_POSTGRES_DSN=dsn,SALES_IDENTITIES_PATH=str(identity),SALES_MODEL_ENABLED='false')
    env.pop('SALES_CONNECTORS_PATH',None)
    server=None;engine=None
    log=(folder/'runtime.log').open('w')
    try:
        server=subprocess.Popen([sys.executable,'-m','uvicorn','backend.app:from_environment','--factory','--host','127.0.0.1','--port','8044','--no-access-log'],env=env,stdout=log,stderr=log)
        for _ in range(40):
            try:
                if httpx.get('http://127.0.0.1:8044/health/ready',trust_env=False,timeout=1).status_code==200:break
            except httpx.HTTPError:pass
            time.sleep(.25)
        else:raise RuntimeError('Native server readiness failed')
        command=('n8n import:credentials --input=/lab/credentials.json && '
                 'n8n import:workflow --input=/lab/workflows.json && '
                 f'n8n execute --id={ids[0]} && n8n execute --id={ids[1]}')
        args=['docker','run','--pull','never','--name',name,'--label','sales.phase7.owner=n8n-execute','--memory','512m','--memory-swap','512m','--cpus','0.5','--pids-limit','96','-e','NODE_OPTIONS=--max-old-space-size=320','-e','N8N_DIAGNOSTICS_ENABLED=false','-e','N8N_VERSION_NOTIFICATIONS_ENABLED=false','--mount',f'type=volume,source={name}-data,target=/home/node/.n8n','--mount',f'type=bind,source={folder},target=/lab,readonly','--entrypoint','/bin/sh','sha256:673cf422821d5dda078bda7962e5c48be400745a843041618a2ad2263972a3b9','-c',command]
        if scheduled:
            from scripts.n8n_schedule_probe import run_schedule
            run_schedule(args,folder,ids,log)
        else:
            engine=subprocess.Popen(args,stdout=log,stderr=log)
            engine.wait(timeout=170)
            if engine.returncode:raise RuntimeError('n8n execution failed; inspect private runtime log')
        state=workflow.get(worker,job['id'])
        assert state['status']=='awaiting_approval' and state['proposal_id']
        assert owner.execute('SELECT count(*) FROM proposals WHERE tenant_id=%s',(tenant,)).fetchone()[0]==1
        assert owner.execute('SELECT count(*) FROM operations WHERE tenant_id=%s',(tenant,)).fetchone()[0]==0
        mode='three-minute Schedule Trigger' if normal else ('accelerated Schedule Trigger/restart' if scheduled else 'CLI execution')
        result={'status':'passed','job_status':state['status'],'proposals':1,'operations':0,'scope':f'Real n8n {mode} with shared domain HTTP/PostgreSQL; synthetic commitment, no model or effects'}
        (folder/'result.json').write_text(json.dumps(result,indent=2))
        checks=['n8n_real_intake_http_postgres_proposal','n8n_wait_poll_preserves_single_proposal','n8n_real_due_workflow_execution','unapproved_flow_zero_effect_operations']
        if normal:checks+=[('actual_three_minute_trigger_both_workflows' if os.environ.get('SALES_N8N_SINGLE_CYCLE')=='enabled'
                            else 'actual_three_minute_cadence_two_completed_cycles_each_workflow')]
        elif scheduled:checks+=['actual_schedule_trigger_both_workflows','same_persisted_wait_execution_resumed_after_container_restart']
        return checks
    finally:
        subprocess.run(['docker','stop','--time','5',name],capture_output=True,timeout=20)
        if engine and engine.poll() is None:engine.kill();engine.wait()
        if server and server.poll() is None:
            if os.name=='nt':subprocess.run(['taskkill','/PID',str(server.pid),'/T','/F'],capture_output=True,timeout=15)
            else:server.terminate()
            server.wait(timeout=10)
        log.close()
