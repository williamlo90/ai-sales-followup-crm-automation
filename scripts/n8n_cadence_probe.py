"""Observe actual Schedule Trigger behavior using the exported interval."""
import json,os,subprocess,time
from datetime import datetime,timezone

def observe(name,folder,ids,engine):
    single=os.environ.get('SALES_N8N_SINGLE_CYCLE')=='enabled'
    start=time.monotonic();deadline=start+(390 if single else 570)
    code="const{DatabaseSync}=require('node:sqlite');const d=new DatabaseSync('/home/node/.n8n/database.sqlite',{readOnly:true});console.log(JSON.stringify(d.prepare('SELECT id,status,mode,workflowId,startedAt FROM execution_entity ORDER BY id').all()));d.close()"
    while time.monotonic()<deadline:
        if engine.poll() is not None:raise RuntimeError('Engine exited during cadence observation')
        response=subprocess.run(['docker','exec',name,'node','-e',code],capture_output=True,text=True,timeout=8)
        if response.returncode:
            time.sleep(3);continue
        rows=json.loads(response.stdout)
        if any(r['status'] in ('error','crashed','canceled') for r in rows):raise RuntimeError('Scheduled execution failed')
        if single:
            intake=[r for r in rows if r['workflowId']==ids[0] and r['mode']=='trigger' and r['status'] in {'waiting','success'}]
            due=[r for r in rows if r['workflowId']==ids[1] and r['mode']=='trigger' and r['status']=='success']
            (folder/'cadence-progress.json').write_text(json.dumps({'elapsed_seconds':round(time.monotonic()-start,1),'intake_trigger_seen':bool(intake),'due_trigger_success':bool(due)}))
            if intake and due:
                result={'status':'passed','configured_interval_seconds':180,'intake_trigger_status':intake[0]['status'],
                        'due_trigger_status':due[0]['status'],'elapsed_seconds':round(time.monotonic()-start,2),
                        'scope':'One actual trigger for each configured three-minute export; no sustained cadence claim'}
                (folder/'cadence-result.json').write_text(json.dumps(result,indent=2));return
            time.sleep(3);continue
        complete={ident:[r for r in rows if r['workflowId']==ident and r['status']=='success'] for ident in ids}
        (folder/'cadence-progress.json').write_text(json.dumps({'elapsed_seconds':round(time.monotonic()-start,1),'successful_cycles':[len(complete[i]) for i in ids],'statuses':[r['status'] for r in rows]}))
        if all(len(v)>=2 for v in complete.values()):
            intervals=[]
            for ident in ids:
                stamps=[datetime.fromisoformat(r['startedAt'].replace('Z','+00:00')) for r in complete[ident][:2]]
                seconds=(stamps[1]-stamps[0]).total_seconds()
                assert 165<=seconds<=195,seconds
                intervals.append(seconds)
            result={'status':'passed','schedule_interval_seconds':180,'observed_intervals_seconds':intervals,
                    'completed_cycles_per_workflow':[len(complete[i]) for i in ids],
                    'executions':rows,'elapsed_seconds':round(time.monotonic()-start,2),
                    'scope':'Actual unchanged three-minute Schedule Triggers, native domain/PostgreSQL; pending approval, no external effects'}
            (folder/'cadence-result.json').write_text(json.dumps(result,indent=2));return
        time.sleep(3)
    raise RuntimeError('Schedule observation deadline')
