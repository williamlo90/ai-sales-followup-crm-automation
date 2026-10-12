"""Actual schedule and persisted Wait restart, using an isolated engine volume."""
import os
import json
import subprocess
import time


def run_schedule(args, folder, workflow_ids, log):
    name=args[args.index('--name')+1]
    command=('if [ ! -f /home/node/.n8n/probe-ready ]; then '
        'n8n import:credentials --input=/lab/credentials.json && '
        'n8n import:workflow --input=/lab/workflows.json && '+
        ' && '.join('n8n publish:workflow --id='+i for i in workflow_ids)+
        ' && touch /home/node/.n8n/probe-ready || exit 1; fi; exec n8n start')
    args=list(args);args[-1]=command
    engine=subprocess.Popen(args,stdout=log,stderr=log)
    def query():
        code="const{DatabaseSync}=require('node:sqlite');const db=new DatabaseSync('/home/node/.n8n/database.sqlite',{readOnly:true});console.log(JSON.stringify(db.prepare('SELECT id,status,mode,workflowId,waitTill FROM execution_entity ORDER BY id').all()));db.close()"
        result=subprocess.run(['docker','exec',name,'node','-e',code],capture_output=True,text=True,timeout=5)
        if result.returncode:return []
        return json.loads(result.stdout)
    try:
        if os.environ.get('SALES_N8N_NORMAL_CADENCE')=='enabled':
            from scripts.n8n_cadence_probe import observe
            observe(name,folder,workflow_ids,engine)
            return
        deadline=time.monotonic()+160;waiting=None
        while time.monotonic()<deadline:
            if engine.poll() is not None:raise RuntimeError('Engine server exited')
            rows=query()
            waiting=next((r for r in rows if r['workflowId']==workflow_ids[0] and r['status']=='waiting'),None)
            if waiting:break
            time.sleep(2)
        if not waiting:raise RuntimeError('No persisted schedule wait observed')
        state=json.loads(subprocess.check_output(['docker','inspect',name],text=True))[0]
        if state['Config']['Labels'].get('sales.phase7.owner')!='n8n-execute' or state['HostConfig']['Memory']!=536870912:
            raise RuntimeError('Unexpected engine ownership or limit')
        before=state['State']['StartedAt']
        subprocess.run(['docker','restart','--time','5',state['Id']],capture_output=True,check=True,timeout=20)
        after=json.loads(subprocess.check_output(['docker','inspect',name],text=True))[0]['State']['StartedAt']
        assert before!=after
        deadline=time.monotonic()+150;resumed=None
        while time.monotonic()<deadline:
            rows=query();resumed=next((r for r in rows if r['id']==waiting['id']),None)
            due=any(r['workflowId']==workflow_ids[1] and r['status']=='success' for r in rows)
            if resumed and resumed['status']=='success' and due:break
            if resumed and resumed['status'] in {'error','crashed','canceled'}:raise RuntimeError('Waiting execution did not recover')
            time.sleep(2)
        else:raise RuntimeError('Resume deadline')
        result={'initial_execution':waiting,'resumed_execution':resumed,'container_start_changed':True,
                'due_schedule_success':due,'schedule_interval_seconds':10,'wait_seconds':90,
                'scope':'Real Schedule Trigger at accelerated lab cadence; same persisted execution resumed after controlled container restart'}
        (folder/'schedule-result.json').write_text(json.dumps(result,indent=2))
    finally:
        subprocess.run(['docker','stop','--time','5',name],capture_output=True,timeout=20)
        if engine.poll() is None:engine.wait(timeout=10)
