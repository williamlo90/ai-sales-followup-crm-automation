"""Actual owned-engine downtime with a durable queued job; no clock override."""
import json
import subprocess
import time
from scripts.connected_workload_steps import run as workload


def run(http,call,cfg,folder):
    name=(folder/'engine-name.txt').read_text()
    for _ in range(90):
        check=subprocess.run(['docker','exec',name,'node','-e',
            "fetch('http://127.0.0.1:5678/healthz').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"],capture_output=True,timeout=5)
        if check.returncode==0:break
        time.sleep(1)
    else:raise RuntimeError('Engine startup deadline')
    state=json.loads(subprocess.check_output(['docker','inspect',name],text=True))[0]
    assert state['Config']['Labels'].get('sales.phase7.owner')=='connected-lab'
    assert state['HostConfig']['Memory']==536870912
    started=state['State']['StartedAt']
    subprocess.run(['docker','stop','--time','5',name],capture_output=True,check=True,timeout=25)
    stopped_at=time.monotonic()
    assert subprocess.check_output(['docker','inspect','--format','{{.State.Running}}',name],text=True).strip()=='false'
    observations=[]
    def after_enqueue(job):
        for _ in range(7):
            observed=call(http,'GET','/v1/workflows/jobs/'+job['id'])
            assert observed['status']=='queued' and observed['proposal_id'] is None and observed['operation_id'] is None
            observations.append({'status':'queued','elapsed_seconds':time.monotonic()-stopped_at})
            time.sleep(5)
        downtime=time.monotonic()-stopped_at
        assert downtime>=35
        subprocess.run(['docker','start',name],capture_output=True,check=True,timeout=20)
        resumed=json.loads(subprocess.check_output(['docker','inspect',name],text=True))[0]
        assert resumed['State']['StartedAt']!=started
        (folder/'missed-schedule.json').write_text(json.dumps({
            'actual_engine_downtime_seconds':downtime,'lab_interval_seconds':10,
            'minimum_missed_intervals':3,'queued_observations':observations,
            'container_start_changed':True},indent=2))
        for _ in range(90):
            running=subprocess.check_output(['docker','inspect','--format','{{.State.Running}}',name],text=True).strip()
            if running!='true':raise RuntimeError('Restarted engine exited before readiness')
            ready=subprocess.run(['docker','exec',name,'node','-e',
                "fetch('http://127.0.0.1:5678/healthz').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"],capture_output=True,timeout=5)
            if ready.returncode==0:break
            time.sleep(1)
        else:raise RuntimeError('Restarted engine readiness deadline')
    result=workload(http,call,cfg,folder,profiles=[('missed_schedule_recovery',1,None)],after_enqueue=after_enqueue)
    result['scope']='Actual n8n stopped through at least three lab intervals; queued job recovered to one verified Odoo operation'
    result['downtime']=json.loads((folder/'missed-schedule.json').read_text())
    result['limitations']=['10-second lab cadence','Controlled engine stop/start, not host reboot',
                            'Seeded input and automated separate lab approval','No model or email calls']
    return result
