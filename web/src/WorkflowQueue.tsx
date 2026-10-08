import {useEffect,useState} from 'react';
type Job={id:string;deal_id:string;journey:string;status:string;proposal_id:string|null;operation_id:string|null;error_code:string|null};

export function WorkflowQueue({token,role}:{token:string;role:string}){
  const [jobs,setJobs]=useState<Job[]>([]),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  async function request(path:string,action?:string){
    const response=await fetch(path,{method:action?'POST':'GET',headers:{Authorization:`Bearer ${token}`,'Content-Type':'application/json'},
      body:action?JSON.stringify({action}):undefined});
    const data=await response.json();if(!response.ok)throw Error(data.error||'Workflow request failed');return data;
  }
  async function refresh(){setJobs((await request('/v1/workflows/jobs')).items);}
  async function run(action:()=>Promise<void>){setBusy(true);setError('');try{await action();}catch(e){setError(e instanceof Error?e.message:'Workflow request failed');}finally{setBusy(false);}}
  useEffect(()=>{let cancelled=false;void request('/v1/workflows/jobs').then(data=>{if(!cancelled)setJobs(data.items);}).catch(()=>{if(!cancelled)setError('Unable to load workflow status');});return()=>{cancelled=true;};},[token]);
  return <section aria-label="Workflow recovery" className="workflow-panel"><div className="sectiontitle"><h2>Workflow recovery</h2><button disabled={busy} onClick={()=>void run(refresh)}>Refresh workflows</button></div>
    <p className="muted">Recovery queues a backend check. It does not grant approval or send a message directly.</p>
    {error&&<p role="alert">{error.replaceAll('_',' ')}</p>}
    {!jobs.length?<p>No workflow jobs in your scope.</p>:jobs.map(job=>{
      const recoverable=['review','disabled','unknown'].includes(job.status);
      const action=job.operation_id?'observe':job.error_code==='proposal_expired'?'renew_expired':'recheck';
      const label=action==='observe'?'Observe recorded result':action==='renew_expired'?'Renew expired proposal':'Recheck prerequisites';
      return <div key={job.id} className="approval"><div><strong>{job.deal_id} · {job.journey} · {job.status.replaceAll('_',' ')}</strong>
        {job.error_code&&<p>{job.error_code.replaceAll('_',' ')}</p>}
        {action==='renew_expired'&&recoverable&&<p>A new proposal requires new approval. Previous approvals stay with the expired version.</p>}
      </div>{recoverable&&['operator','worker'].includes(role)&&<button disabled={busy} onClick={()=>void run(async()=>{await request(`/v1/workflows/jobs/${job.id}/recover`,action);await refresh();})}>{label}</button>}</div>;
    })}
  </section>;
}
