import {useState} from 'react';

export function ProposalHandoff({token,id,role,stale,commitmentBound}:{token:string;id:string;role:string;stale:boolean;commitmentBound:boolean}){
  const [busy,setBusy]=useState(false),[message,setMessage]=useState(''),[error,setError]=useState('');
  async function handoff(kind:string){setBusy(true);setMessage('');setError('');try{
    const response=await fetch(`/v1/proposals/${encodeURIComponent(id)}/handoff/${kind}`,{method:'POST',headers:{Authorization:`Bearer ${token}`}});
    const data=await response.json();if(!response.ok)throw Error(data.error||'Handoff failed');
    setMessage(kind==='crm'
      ?`Queued CRM activity for the configured worker. Job: ${data.id}. Approval and eligibility are checked before execution.`
      :`Queued email follow-up for the configured worker. Job: ${data.id}. Sending requires approval, due time, and project configuration.`);
  }catch(e){setError(e instanceof Error?e.message:'Handoff failed');}finally{setBusy(false);}}
  if(role!=='operator')return null;
  return <section className="handoff"><h3>Release to workflow</h3><p>Queue actions for the worker. It checks approval, eligibility and due time before execution.</p>
    {!commitmentBound&&<p>Record a source-backed commitment through Intake before queueing this proposal.</p>}
    <button disabled={busy||stale||!commitmentBound} onClick={()=>handoff('crm')}>Queue CRM activity</button>
    <button disabled={busy||stale||!commitmentBound} onClick={()=>handoff('email')}>Queue email follow-up</button>
    {message&&<p role="status">{message}</p>}{error&&<p role="alert">{error.replaceAll('_',' ')}</p>}
  </section>;
}
