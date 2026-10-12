import { useState, useEffect, type FormEvent } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';
import { WorkflowQueue } from './WorkflowQueue';
import { IntakeReview } from './IntakeReview';
import { ProposalHandoff } from './ProposalHandoff';
import { ConnectorBinding } from './ConnectorBinding';

type Actor = {id:string;role:string;tenant_id:string;deal_ids:string[]};
type Operation = {id:string;kind:'crm'|'email';status:string;recovery:string|null};
type Proposal = {id:string;payload_hash:string;status:string;validation_error:string|null;approval_valid:boolean;
  approvals:{kind:string;actor_id:string}[];payload:{deal_id:string;account_id:string;recipient:string;summary:string;due_at:string;draft:string;evidence:{source_id:string;revision:number;quote:string}[]}};

function readableDate(value:string){
  const date=new Date(value);
  return Number.isNaN(date.getTime())?value:`${new Intl.DateTimeFormat('en-GB',{dateStyle:'medium',timeStyle:'short',timeZone:'Asia/Jakarta'}).format(date)} WIB`;
}

function App(){
  const [token,setToken]=useState('');
  const [actor,setActor]=useState<Actor|null>(null);
  const [items,setItems]=useState<Proposal[]>([]);
  const [selected,setSelected]=useState<Proposal|null>(null);
  const [error,setError]=useState('');
  const [busy,setBusy]=useState(false);
  const [notice,setNotice]=useState('');
  const [operations,setOperations]=useState<Operation[]>([]);
  async function api(path:string, method='GET', data?:unknown){
    const result=await fetch(path,{method,headers:{Authorization:`Bearer ${token}`,'Content-Type':'application/json'},body:data===undefined?undefined:JSON.stringify(data)});
    const value=await result.json();
    if(!result.ok) throw new Error(value.error||`Request failed (${result.status})`);
    return value;
  }
  useEffect(()=>{let cancelled=false;setOperations([]);if(selected&&actor){void api(`/v1/proposals/${selected.id}/operations`).then(data=>{if(!cancelled)setOperations(data.items);}).catch(()=>{if(!cancelled)setError('Unable to load operation status. Refresh before acting.');});}return()=>{cancelled=true;};},[selected,actor,token]);
  async function run(action:()=>Promise<void>){setBusy(true);setError('');setNotice('');try{await action();}catch(e){setError(e instanceof Error?e.message:'Request failed');}finally{setBusy(false);}}
  async function refresh(){const data=await api('/v1/proposals');setItems(data.items);if(selected){setSelected(data.items.find((p:Proposal)=>p.id===selected.id)||null);}}
  function signIn(e:FormEvent){e.preventDefault();void run(async()=>{const current=await api('/v1/me'); const data=await api('/v1/proposals');setActor(current);setItems(data.items);setSelected(null);});}
  function signOut(){setToken('');setActor(null);setItems([]);setSelected(null);setError('');setNotice('');}
  function prepare(e:FormEvent<HTMLFormElement>){e.preventDefault();const form=new FormData(e.currentTarget);void run(async()=>{
    const data={deal_id:form.get('deal'),deal_version:Number(form.get('version')),summary:form.get('summary'),due_at:form.get('due'),draft:form.get('draft'),
      evidence:[{source_id:form.get('source'),revision:Number(form.get('revision')),quote:form.get('quote')}]};
    const p=await api('/v1/proposals','POST',data);await refresh();setSelected(p);setNotice('Proposal prepared. Review the source and proposed content before approval.');
  });}
  function approve(kind:'crm'|'email'){if(!selected)return;void run(async()=>{const p=await api(`/v1/proposals/${selected.id}/approvals`,'POST',{kind,payload_hash:selected.payload_hash});await refresh();setSelected(p);setNotice(`${kind==='crm'?'CRM':'Email'} approval recorded. Check Action outcomes for execution status.`);});}
  const status=selected?.validation_error?'Review required':operations.some(op=>op.recovery)?'Needs reconciliation':operations.some(op=>op.status==='verified'||op.status==='accepted')?'Action recorded':selected?.approvals.length===2?'Approved':'Awaiting review';
  return <div className="app"><header><div className="brand"><span className="brandmark">SF</span><span>Sales follow-up</span></div><div className="lab"><span className="environment-dot"/> LOCAL WORKSPACE</div></header>
    <main><div className="heading"><div><p className="eyebrow">SALES OPERATIONS / REVIEW</p><h1>Follow-up desk</h1><p>Review the evidence, approve the next action, and track the result.</p></div>{actor&&<div className="identity"><span className="role-label">{actor.role}</span><button onClick={signOut} disabled={busy}>Sign out</button></div>}</div>
    {error&&<div role="alert" className="alert">{error.replaceAll('_',' ')}</div>}{notice&&<div role="status" className="notice">{notice}</div>}
    {!actor?<section className="login"><h2>Open your workspace</h2><p>Use your assigned local access token. Your role and deal access are checked by the server.</p><form onSubmit={signIn}><label>Access token<input type="password" autoComplete="off" value={token} onChange={e=>setToken(e.target.value)} required maxLength={256}/></label><button className="primary" disabled={busy}>{busy?'Connecting…':'Continue'}</button></form></section>:
    <div className="workspace"><aside><div className="sectiontitle"><div><p className="eyebrow">01 / INBOX</p><h2>Review queue <span className="queue-count">{items.length}</span></h2></div><button disabled={busy} onClick={()=>void run(refresh)}>Refresh</button></div>{items.length===0?<p className="empty">No proposals yet. Prepare a follow-up from a recorded conversation.</p>:<nav aria-label="Proposals">{items.map(p=><button className={'queueitem '+(selected?.id===p.id?'selected':'')} key={p.id} onClick={()=>setSelected(p)}><span>{p.payload.summary}</span><small>{p.payload.deal_id} · {p.validation_error?'Needs new review':`${p.approvals.length}/2 approvals`}</small></button>)}</nav>}
      {(actor.role==='operator')&&<details open={!selected}><summary>Prepare a proposal</summary><form onSubmit={prepare} className="prepare"><div className="pair"><label>Deal ID<input name="deal" defaultValue="deal-1" required/></label><label>CRM version<input name="version" type="number" min="1" defaultValue="1" required/></label></div><div className="pair"><label>Source ID<input name="source" defaultValue="thread-1" required/></label><label>Source revision<input name="revision" type="number" min="1" defaultValue="1" required/></label></div><label>Exact source quote<textarea name="quote" required defaultValue="15 October 2026 at 14:00 Asia/Jakarta"/></label><label>Activity summary<input name="summary" required maxLength={500} defaultValue="Confirm rescheduled demo"/></label><label>Due date and time (with UTC offset)<input name="due" required defaultValue="2026-10-15T14:00:00+07:00"/></label><label>Follow-up draft<textarea name="draft" required rows={4} defaultValue="We have noted the revised demo time: 15 October 2026 at 14:00 Asia/Jakarta."/></label><button className="primary" disabled={busy}>Prepare for review</button></form></details>}</aside>
      <article>{!selected?<div className="placeholder"><p className="eyebrow">02 / DECISION</p><h2>Select a follow-up to review.</h2><p>Source evidence, CRM action and the email draft will appear here.</p></div>:<><div className="sectiontitle proposal-title"><div><p className="eyebrow">02 / DECISION · {selected.payload.deal_id}</p><h2>{selected.payload.summary}</h2><p className="proposal-context">For {selected.payload.account_id} · Due {readableDate(selected.payload.due_at)}</p></div><span className={'badge '+(status==='Action recorded'?'complete':status==='Needs reconciliation'||status==='Review required'?'warning':'')}>{status}</span></div>
      {selected.validation_error&&<div className="alert">This proposal is no longer eligible: {selected.validation_error.replaceAll('_',' ')}. Existing approvals cannot be used.</div>}
      {operations.length>0&&<section className="outcome-section"><h3>Action outcomes</h3>{operations.map(op=><div key={op.id} className={op.recovery?'alert':'notice'}><strong>{op.kind==='crm'?'CRM activity':'Email'} · {op.status==='unknown'||op.status==='dispatched'?'Outcome unknown':op.status==='verified'?'CRM result verified':op.status==='accepted'?'Accepted / sent observed':op.status}</strong><p>{op.recovery?'Reconcile the recorded operation before attempting another action. A lost response may hide a completed action.':op.kind==='email'?'Acceptance or Sent Items does not establish delivery or read status.':'The recorded outcome is available for review.'}</p><details className="technical-details"><summary>Operation reference</summary><code>{op.id}</code></details></div>)}</section>}
      <section className="evidence-section"><h3>Source evidence</h3>{selected.payload.evidence.map((ev,i)=><blockquote key={i}><p>{ev.quote}</p><footer>{ev.source_id} · revision {ev.revision}</footer></blockquote>)}</section>
      <div className="decision-grid"><section><p className="eyebrow">01 / CRM</p><h3>Proposed CRM activity</h3><dl><dt>Action</dt><dd>Create a follow-up activity</dd><dt>Summary</dt><dd>{selected.payload.summary}</dd><dt>Due</dt><dd>{readableDate(selected.payload.due_at)}</dd></dl><Approval kind="crm" proposal={selected} actor={actor} busy={busy} onApprove={()=>approve('crm')}/></section>
      <section><p className="eyebrow">02 / EMAIL</p><h3>Follow-up draft</h3><p className="recipient">To: {selected.payload.recipient}</p><div className="draft">{selected.payload.draft}</div><p className="muted">Review factual accuracy against the source. Approval records consent; sending is currently disabled.</p><Approval kind="email" proposal={selected} actor={actor} busy={busy} onApprove={()=>approve('email')}/></section></div>
      <ConnectorBinding key={"binding-"+selected.id} token={token} id={selected.id} role={actor.role} stale={!!selected.validation_error}/><ProposalHandoff key={selected.id} token={token} id={selected.id} role={actor.role} stale={!!selected.validation_error}/><details><summary>Proposal reference</summary><p className="reference">{selected.id}<br/>Payload: {selected.payload_hash}</p></details></>}</article></div>}
    {actor?.role==='operator'&&<IntakeReview token={token} onPrepared={async()=>{await refresh();}}/>}
    {actor&&<WorkflowQueue token={token} role={actor.role}/>}
    <footer className="footnote">Local review environment · Approved CRM actions may run through the configured workflow. Check Action outcomes for results.</footer></main></div>;
}
function Approval({kind,proposal,actor,busy,onApprove}:{kind:'crm'|'email';proposal:Proposal;actor:Actor;busy:boolean;onApprove:()=>void}){
  const approval=proposal.approvals.find(a=>a.kind===kind);
  return <div className="approval">{approval?<span>{proposal.validation_error?'Previous approval':'Approved'} by {approval.actor_id}</span>:<span>Awaiting {kind==='crm'?'CRM':'email'} approval</span>}{actor.role==='approver'&&!approval&&<button className="primary" disabled={busy||!!proposal.validation_error} onClick={onApprove}>Approve {kind==='crm'?'CRM activity':'email draft'}</button>}</div>;
}
createRoot(document.getElementById('root')!).render(<App/>);
