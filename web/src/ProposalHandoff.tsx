import {useState} from 'react';

export function ProposalHandoff({token,id,role,stale}:{token:string;id:string;role:string;stale:boolean}){
  const [busy,setBusy]=useState(false),[message,setMessage]=useState(''),[error,setError]=useState('');
  async function handoff(kind:string){setBusy(true);setMessage('');setError('');try{
    const response=await fetch(`/v1/proposals/${encodeURIComponent(id)}/handoff/${kind}`,{method:'POST',headers:{Authorization:`Bearer ${token}`}});
    const data=await response.json();if(!response.ok)throw Error(data.error||'Handoff failed');
    setMessage(kind==='crm'
      ?`Queued CRM activity for the configured worker. Job: ${data.id}. Approval and eligibility are checked before execution.`
      :`Queued email job: ${data.id}. Email sending is disabled in local V1; this job will not deliver a message.`);
  }catch(e){setError(e instanceof Error?e.message:'Handoff failed');}finally{setBusy(false);}}
  if(role!=='operator')return null;
  return <section><h3>Workflow handoff</h3><p>Queue this proposal for the configured worker. Queueing does not approve or execute an action. Email sending is disabled in local V1.</p>
    <button disabled={busy||stale} onClick={()=>handoff('crm')}>Queue CRM activity</button>{' '}
    <button disabled={busy||stale} onClick={()=>handoff('email')}>Queue email job (sending off)</button>
    {message&&<p role="status">{message}</p>}{error&&<p role="alert">{error.replaceAll('_',' ')}</p>}
  </section>;
}
