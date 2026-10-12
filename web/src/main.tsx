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
  const [operationState,setOperationState]=useState<{proposalId:string;items:Operation[]}>({proposalId:'',items:[]});
  const operations=operationState.proposalId===selected?.id?operationState.items:[];
  async function api(path:string, method='GET', data?:unknown){
    const result=await fetch(path,{method,headers:{Authorization:`Bearer ${token}`,'Content-Type':'application/json'},body:data===undefined?undefined:JSON.stringify(data)});
    const value=await result.json();
    if(!result.ok) throw new Error(value.error||`Request failed (${result.status})`);
    return value;
  }
  useEffect(()=>{let cancelled=false;if(selected&&actor){const id=selected.id;void api(`/v1/proposals/${id}/operations`).then(data=>{if(!cancelled)setOperationState({proposalId:id,items:data.items});}).catch(()=>{if(!cancelled)setError('Unable to load operation status. Refresh before acting.');});}return()=>{cancelled=true;};},[selected,actor,token]);
  async function run(action:()=>Promise<void>){setBusy(true);setError('');setNotice('');try{await action();}catch(e){setError(e instanceof Error?e.message:'Request failed');}finally{setBusy(false);}}
  async function refresh(){const data=await api('/v1/proposals');setItems(data.items);if(selected){setSelected(data.items.find((p:Proposal)=>p.id===selected.id)||null);}}
  function signIn(e:FormEvent){e.preventDefault();void run(async()=>{const current=await api('/v1/me');const data=await api('/v1/proposals');setActor(current);setItems(data.items);setSelected(null);});}
  function signOut(){setToken('');setActor(null);setItems([]);setSelected(null);setError('');setNotice('');}
  function prepare(e:FormEvent<HTMLFormElement>){e.preventDefault();const form=new FormData(e.currentTarget);void run(async()=>{
    const data={deal_id:form.get('deal'),deal_version:Number(form.get('version')),summary:form.get('summary'),due_at:form.get('due'),draft:form.get('draft'),
      evidence:[{source_id:form.get('source'),revision:Number(form.get('revision')),quote:form.get('quote')}]};
    const p=await api('/v1/proposals','POST',data);await refresh();setSelected(p);setNotice('Proposal prepared. Review the source and proposed content before approval.');
  });}
  function approve(kind:'crm'|'email'){if(!selected)return;void run(async()=>{const p=await api(`/v1/proposals/${selected.id}/approvals`,'POST',{kind,payload_hash:selected.payload_hash});await refresh();setSelected(p);setNotice(`${kind==='crm'?'CRM':'Email'} approval recorded. Check Action outcomes for execution status.`);});}
  const status=selected?.validation_error?'Review required':operations.some(op=>op.recovery)?'Needs reconciliation':operations.some(op=>op.status==='verified'||op.status==='accepted')?'Action recorded':selected?.approvals.length===2?'Approved':'Awaiting review';
  return <div className="app">
    <header className="topbar"><div className="topbar-inner"><div className="brand"><span className="brandmark">SF</span><span>Sales follow-up</span></div><nav className="topnav" aria-label="Workspace"><a className="active" href="#review-desk">Review desk</a>{actor?.role==='operator'&&<a href="#conversation-intake">Intake</a>}{actor&&<a href="#workflow-recovery">Recovery</a>}</nav><div className="topbar-right"><span className="environment-dot"/><span>LOCAL WORKSPACE</span></div></div></header>
    <main><div className="heading"><div><p className="eyebrow">CUSTOMER OPERATIONS</p><h1>Follow-ups</h1><p>Evidence and approval, in one place.</p></div>{actor&&<div className="identity"><span className="role-label">{actor.role}</span><button onClick={signOut} disabled={busy}>Sign out</button></div>}</div>
    {error&&<div role="alert" className="alert">{error.replaceAll('_',' ')}</div>}{notice&&<div role="status" className="notice">{notice}</div>}
    {!actor?<section className="login"><p className="eyebrow">SECURE ACCESS</p><h2>Open your workspace</h2><p>Use your assigned local access token. Your role and deal access are checked by the server.</p><form onSubmit={signIn}><label>Access token<input type="password" autoComplete="off" value={token} onChange={e=>setToken(e.target.value)} required maxLength={256}/></label><button className="primary" disabled={busy}>{busy?'Connecting…':'Continue'}</button></form></section>:
    <div className="workspace" id="review-desk">
      <aside className="queue-panel"><div className="queue-heading"><div><p className="eyebrow">YOUR INBOX</p><h2>Review queue</h2></div><span className="queue-count">{items.length}</span></div><button className="refresh-button" disabled={busy} onClick={()=>void run(refresh)}>Refresh list</button>
        {items.length===0?<p className="empty">No proposals yet. Prepare a follow-up from a recorded conversation.</p>:<nav aria-label="Proposals">{items.map(p=><button className={'queueitem '+(selected?.id===p.id?'selected':'')} key={p.id} onClick={()=>setSelected(p)}><span className="queueitem-title">{p.payload.summary}</span><span className="queueitem-account">{p.payload.account_id}</span><span className="queueitem-meta">{p.payload.deal_id} <span aria-hidden="true">·</span> {p.validation_error?'Needs new review':`${p.approvals.length}/2 approvals`}</span></button>)}</nav>}
        {actor.role==='operator'&&<details className="prepare-drawer" open={!selected}><summary>Prepare a proposal</summary><form onSubmit={prepare} className="prepare"><div className="pair"><label>Deal ID<input name="deal" defaultValue="deal-1" required/></label><label>CRM version<input name="version" type="number" min="1" defaultValue="1" required/></label></div><div className="pair"><label>Source ID<input name="source" defaultValue="thread-1" required/></label><label>Source revision<input name="revision" type="number" min="1" defaultValue="1" required/></label></div><label>Exact source quote<textarea name="quote" required defaultValue="Thanks for sharing the revised 25-seat proposal. Please call me on 15 October 2026 at 14:00 Asia/Jakarta to discuss pricing, and email me the call details."/></label><label>Activity summary<input name="summary" required maxLength={500} defaultValue="Call Northstar about 25-seat proposal"/></label><label>Due date and time (with UTC offset)<input name="due" required defaultValue="2026-10-15T14:00:00+07:00"/></label><label>Follow-up draft<textarea name="draft" required rows={4} defaultValue="Thanks for your note about the revised 25-seat proposal. I will call you on 15 October 2026 at 14:00 Asia/Jakarta to discuss pricing."/></label><button className="primary" disabled={busy}>Prepare for review</button></form></details>}
      </aside>
      <article className="case-panel">{!selected?<div className="placeholder"><p className="eyebrow">REVIEW FILE</p><h2>Select a follow-up.</h2><p>The source, proposed action, and draft will appear here.</p></div>:<>
        <div className="case-heading"><div><p className="eyebrow">REVIEW FILE <span aria-hidden="true">/</span> {selected.payload.deal_id}</p><h2>{selected.payload.summary}</h2><p className="case-account">{selected.payload.account_id} <span aria-hidden="true">·</span> Due {readableDate(selected.payload.due_at)}</p></div><span className={'badge '+(status==='Action recorded'?'complete':status==='Needs reconciliation'||status==='Review required'?'warning':'')}>{status}</span></div>
        {selected.validation_error&&<div className="alert">This proposal is no longer eligible: {selected.validation_error.replaceAll('_',' ')}. Existing approvals cannot be used.</div>}
        <div className="case-body"><div className="case-content">
          <section className="evidence-section"><div className="section-kicker">01 <span>Source</span></div><h3>What the customer said</h3>{selected.payload.evidence.map((ev,i)=><blockquote key={i}><p>{ev.quote}</p><footer>{ev.source_id} · revision {ev.revision}</footer></blockquote>)}</section>
          <section className="crm-section"><div className="section-kicker">02 <span>Proposed action</span></div><h3>Proposed CRM activity</h3><dl><dt>Action</dt><dd>Create a follow-up activity</dd><dt>Summary</dt><dd>{selected.payload.summary}</dd><dt>Due</dt><dd>{readableDate(selected.payload.due_at)}</dd></dl></section>
          <section className="email-section"><div className="section-kicker">03 <span>Customer message</span></div><h3>Follow-up draft</h3><div className="mail-preview"><div className="mail-envelope"><span>To</span><strong>{selected.payload.recipient}</strong></div><div className="draft">{selected.payload.draft}</div></div><p className="muted">Review the facts against the source before approving this draft.</p></section>
        </div><aside className="decision-panel"><p className="eyebrow">REVIEW & RELEASE</p><h3>Decision</h3><p className="decision-intro">CRM and email need separate approval. Each decision is tied to this exact proposal.</p>
          <div className="decision-item"><p className="decision-name">CRM activity</p><Approval kind="crm" proposal={selected} actor={actor} busy={busy} onApprove={()=>approve('crm')}/></div>
          <div className="decision-item"><p className="decision-name">Email draft</p><Approval kind="email" proposal={selected} actor={actor} busy={busy} onApprove={()=>approve('email')}/></div>
          <section className="outcome-section"><h3>Action outcomes</h3>{operations.length===0?<p className="muted">No action recorded yet.</p>:operations.map(op=><div key={op.id} className={op.recovery?'alert':'notice'}><strong>{op.kind==='crm'?'CRM activity':'Email'} · {op.status==='unknown'||op.status==='dispatched'?'Outcome unknown':op.status==='verified'?'CRM result verified':op.status==='accepted'?'Accepted / sent observed':op.status}</strong><p>{op.recovery?'Reconcile the recorded operation before attempting another action. A lost response may hide a completed action.':op.kind==='email'?'Acceptance or Sent Items does not establish delivery or read status.':'The recorded outcome is available for review.'}</p><details className="technical-details"><summary>Operation reference</summary><code>{op.id}</code></details></div>)}</section>
          <p className="release-note">Approval records consent. Sending remains disabled until the configured workflow runs.</p>
        </aside></div>
        <div className="case-technical"><ConnectorBinding key={'binding-'+selected.id} token={token} id={selected.id} role={actor.role} stale={!!selected.validation_error}/><ProposalHandoff key={selected.id} token={token} id={selected.id} role={actor.role} stale={!!selected.validation_error}/><details><summary>Proposal reference</summary><p className="reference">{selected.id}<br/>Payload: {selected.payload_hash}</p></details></div>
      </>}</article>
    </div>}
    {actor?.role==='operator'&&<div id="conversation-intake"><IntakeReview token={token} onPrepared={async()=>{await refresh();}}/></div>}
    {actor&&<div id="workflow-recovery"><WorkflowQueue token={token} role={actor.role}/></div>}
    <footer className="footnote">Local review environment · Results are recorded before a retry or recovery action.</footer></main>
  </div>;
}
function Approval({kind,proposal,actor,busy,onApprove}:{kind:'crm'|'email';proposal:Proposal;actor:Actor;busy:boolean;onApprove:()=>void}){
  const approval=proposal.approvals.find(a=>a.kind===kind);
  return <div className="approval">{approval?<span>{proposal.validation_error?'Previous approval':'Approved'} by {approval.actor_id}</span>:<span>Awaiting {kind==='crm'?'CRM':'email'} approval</span>}{actor.role==='approver'&&!approval&&<button className="primary" disabled={busy||!!proposal.validation_error} onClick={onApprove}>Approve {kind==='crm'?'CRM activity':'email draft'}</button>}</div>;
}
createRoot(document.getElementById('root')!).render(<App/>);
