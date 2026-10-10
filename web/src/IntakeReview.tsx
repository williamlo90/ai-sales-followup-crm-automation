import {useState} from 'react';

type Candidate={id:string;revision:number;owner:string;description:string;due_at:string;state:string;evidence:{source_id:string;revision:number;quote:string}};
type Extraction={status:string;commitments:Candidate[];missing_information:string[];conflicts:string[]};

export function IntakeReview({token,onPrepared}:{token:string;onPrepared:()=>Promise<void>}){
  const [deal,setDeal]=useState('');
  const [loadedDeal,setLoadedDeal]=useState('');
  const [result,setResult]=useState<Extraction|null>(null);
  const [checked,setChecked]=useState<number[]>([]);
  const [done,setDone]=useState<number[]>([]);
  const [busy,setBusy]=useState(false);
  const [message,setMessage]=useState('');
  const [error,setError]=useState('');
  async function api(path:string,body?:unknown){
    const response=await fetch(path,{method:body===undefined?'GET':'POST',headers:{Authorization:`Bearer ${token}`,'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});
    const value=await response.json();if(!response.ok)throw Error(value.error||'Request failed');return value;
  }
  async function run(action:()=>Promise<void>){setBusy(true);setError('');setMessage('');try{await action();}catch(e){setError(e instanceof Error?e.message:'Request failed');}finally{setBusy(false);}}
  function extract(){void run(async()=>{
    setResult(null);setChecked([]);setDone([]);
    const value=await api('/v1/skills/extract_commitments',{deal_id:deal});
    setLoadedDeal(deal);setResult(value.result.extraction);
  });}
  function prepare(candidate:Candidate,index:number){void run(async()=>{
    const recorded=await api(`/v1/deals/${encodeURIComponent(loadedDeal)}/commitments`,candidate);
    if(!['applied','duplicate'].includes(recorded.status))throw Error(`Commitment needs review: ${recorded.reason}`);
    const context=await api(`/v1/deals/${encodeURIComponent(loadedDeal)}/context`);
    await api('/v1/skills/prepare_crm_update',{deal_id:loadedDeal,deal_version:context.deal.version,commitment:{id:candidate.id,revision:candidate.revision}});
    setDone(old=>[...old,index]);setMessage('Proposal prepared in the review queue. CRM and email approvals are still required.');
    await onPrepared();
  });}
  return <section aria-label="Conversation intake"><h2>Review conversation commitments</h2>
    <p>Extract candidates from recorded sources. Review each candidate before preparing a proposal. Extraction uses the configured model; no model runs automatically.</p>
    <label>Conversation deal ID<input value={deal} disabled={busy} onChange={e=>{setDeal(e.target.value);setResult(null);}} maxLength={200}/></label>
    <button disabled={busy||!deal.trim()} onClick={extract}>Extract candidates</button>
    {error&&<p role="alert">{error.replaceAll('_',' ')}</p>}{message&&<p role="status">{message}</p>}
    {result&&<><p>Deal: {loadedDeal} · {result.status}</p>
      {[...result.missing_information,...result.conflicts].map((reason,i)=><p key={i} className="alert">{reason}</p>)}
      {result.status!=='ready'&&<p>Resolve missing information or conflicting sources before extracting again.</p>}
      {result.commitments.length===0&&<p>No commitment candidates returned.</p>}
      {result.commitments.map((candidate,index)=><section key={`${candidate.id}-${candidate.revision}`}>
        <h3>{candidate.description}</h3><p>{candidate.owner} · {candidate.due_at} · {candidate.state}</p>
        <blockquote>{candidate.evidence.quote}<footer>{candidate.evidence.source_id} · revision {candidate.evidence.revision}</footer></blockquote>
        <label><input type="checkbox" checked={checked.includes(index)} disabled={busy||done.includes(index)} onChange={e=>setChecked(old=>e.target.checked?[...old,index]:old.filter(i=>i!==index))}/>I checked the owner, date and commitment against the source.</label>
        <button disabled={busy||result.status!=='ready'||candidate.state!=='active'||!checked.includes(index)||done.includes(index)} onClick={()=>prepare(candidate,index)}>{done.includes(index)?'Proposal prepared':'Record and prepare proposal'}</button>
      </section>)}
    </>}
  </section>;
}
