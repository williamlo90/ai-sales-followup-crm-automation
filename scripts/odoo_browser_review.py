"""Real browser review against native factory and scoped PostgreSQL/Odoo."""
import hashlib,json,os,secrets,subprocess,sys,time
from uuid import uuid4
import httpx
from backend.config import ROOT

def review(dsn,actors,cfg,local,binding,mode):
 folder=ROOT/'local/phase-7'/('browser-'+uuid4().hex[:12]);folder.mkdir()
 tokens={r:secrets.token_urlsafe(32) for r in actors}
 (folder/'identities.json').write_text(json.dumps({hashlib.sha256(tokens[r].encode()).hexdigest():a.model_dump(mode='json') for r,a in actors.items()}))
 (folder/'odoo-token').write_text(cfg['operator_token'])
 connector={'local_tenant':actors['worker'].tenant_id,'worker_id':actors['worker'].id,'crm_write_enabled':True,'odoo':{'base_url':cfg['base_url'],'connector_tenant':cfg['tenant'],'company_id':cfg['company_id'],'token_file':str(folder/'odoo-token'),'deals':{'odoo-lab':{'opportunity_id':cfg['opportunity_id'],'assignee_id':cfg['assignee_id']}}}}
 (folder/'connectors.json').write_text(json.dumps(connector))
 (folder/'browser.json').write_text(json.dumps({'tokens':tokens,'summary':local['payload']['summary'],'binding':binding.model_dump(mode='json'),'mode':mode,'screenshot':str(folder/'review.png')}))
 env=os.environ.copy();env.update(SALES_STORAGE='postgresql',SALES_POSTGRES_DSN=dsn,SALES_IDENTITIES_PATH=str(folder/'identities.json'),SALES_CONNECTORS_PATH=str(folder/'connectors.json'),SALES_MODEL_ENABLED='false')
 processes=[]
 with (folder/'runtime.log').open('w') as log:
  try:
   processes.append(subprocess.Popen([sys.executable,'-m','uvicorn','backend.app:from_environment','--factory','--host','127.0.0.1','--port','8040','--no-access-log'],env=env,stdout=log,stderr=log))
   processes.append(subprocess.Popen(['node',str(ROOT/'web/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port','8044','--strictPort'],cwd=ROOT/'web',stdout=log,stderr=log))
   for _ in range(60):
    try:
     if httpx.get('http://127.0.0.1:8044/health/ready',trust_env=False,timeout=1).status_code==200:break
    except httpx.HTTPError:pass
    time.sleep(.25)
   else:raise RuntimeError('browser_app_readiness')
   result=subprocess.run(['node',str(ROOT/'scripts/connected_browser.mjs'),str(folder/'browser.json')],capture_output=True,text=True,timeout=50)
   (folder/'browser.log').write_text(result.stdout+result.stderr)
   if result.returncode:raise RuntimeError('connected_browser_failed')
   (folder/'result.json').write_text(result.stdout)
  finally:
   for process in reversed(processes):
    if process.poll() is None:process.terminate();process.wait(timeout=10)
