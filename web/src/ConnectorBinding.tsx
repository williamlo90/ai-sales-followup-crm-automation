import {useEffect,useState,type FormEvent} from 'react';

export function ConnectorBinding({token,id,role,stale}:{token:string;id:string;role:string;stale:boolean}){
  const [preparation,setPreparation]=useState<{preview:Record<string,string|number>;timezone:string}|null>(null);
  const [binding,setBinding]=useState<Record<string,unknown>|null>(null);
  const [busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
  const path=`/v1/proposals/${encodeURIComponent(id)}/connector-binding`;
  useEffect(()=>{let cancelled=false;setBinding(null);setError('');
    void fetch(path,{headers:{Authorization:`Bearer ${token}`}}).then(async response=>{
      const value=await response.json();if(cancelled)return;
      if(response.ok)setBinding(value);else if(value.error!=='connector_binding_missing')setError(value.error||'Unable to load binding');
    }).catch(()=>{if(!cancelled)setError('Unable to load binding');});return()=>{cancelled=true;};
  },[path,token]);
  async function prepare(){setBusy(true);setError('');try{
    const response=await fetch(`/v1/proposals/${encodeURIComponent(id)}/connector-preparation`,{headers:{Authorization:`Bearer ${token}`}});
    const result=await response.json();if(!response.ok)throw Error(result.error||'Preparation failed');setPreparation(result);
  }catch(e){setError(e instanceof Error?e.message:'Preparation failed');}finally{setBusy(false);}}
  function attach(event:FormEvent<HTMLFormElement>){event.preventDefault();const form=new FormData(event.currentTarget);
    const value=(key:string)=>String(form.get(key)||'');
    const data={connector_tenant:value('connector_tenant'),proposal_id:value('proposal_id'),approval_id:value('approval_id'),actor_id:value('actor_id'),
      preview:{kind:'activity',contract_version:'1.0',company_id:Number(value('company_id')),opportunity_id:Number(value('opportunity_id')),assignee_id:Number(value('assignee_id')),
        due_date:value('due_date'),summary:value('summary'),source_version:value('source_version')}};
    setBusy(true);setError('');setNotice('');
    void fetch(path,{method:'POST',headers:{Authorization:`Bearer ${token}`,'Content-Type':'application/json'},body:JSON.stringify(data)}).then(async response=>{
      const result=await response.json();if(!response.ok)throw Error(result.error||'Binding failed');setBinding(result);setNotice('Binding verified and saved. No CRM action was executed.');
    }).catch(e=>setError(e instanceof Error?e.message:'Binding failed')).finally(()=>setBusy(false));
  }
  return <section><h3>Odoo connector binding</h3>
    <p>Use the activity preview above to prepare an activity in the Odoo connector workspace. Obtain its separate approval, then copy the exact approved references and preview below. The backend checks mapping, dates, summary, approval and freshness before saving.</p>
    <button disabled={busy||stale} onClick={()=>void prepare()}>Load mapped activity preview</button>
    {preparation&&<><p>Create a new activity · timezone {preparation.timezone}. No existing activity is overwritten.</p><table><thead><tr><th>Field</th><th>Before</th><th>Proposed value</th></tr></thead><tbody>{Object.entries(preparation.preview).map(([field,value])=><tr key={field}><td>{field.replaceAll('_',' ')}</td><td>New activity</td><td>{value}</td></tr>)}</tbody></table></>}
    {error&&<p role="alert">{error.replaceAll('_',' ')}</p>}{notice&&<p role="status">{notice}</p>}
    {binding?<><p>Immutable binding saved for this proposal.</p><dl className="binding-details">{Object.entries(binding).map(([key,value])=><div key={key}><dt>{key.replaceAll('_',' ')}</dt><dd>{typeof value==='object'?JSON.stringify(value):String(value)}</dd></div>)}</dl></>:
      ['operator','worker'].includes(role)&&<details><summary>Attach approved connector proposal</summary><form key={JSON.stringify(preparation)} onSubmit={attach}>
        {['connector_tenant','proposal_id','approval_id','actor_id'].map(name=><label key={name}>{`Connector ${name.replaceAll('_',' ')}`}<input name={name} required maxLength={36} disabled={busy||stale}/></label>)}
        {['company_id','opportunity_id','assignee_id'].map(name=><label key={name}>{name.replaceAll('_',' ')}<input defaultValue={preparation?.preview[name]} name={name} type="number" min="1" step="1" required disabled={busy||stale}/></label>)}
        <label>Connector due date<input defaultValue={preparation?.preview.due_date} name="due_date" type="date" required disabled={busy||stale}/></label>
        <label>Connector activity summary<input defaultValue={preparation?.preview.summary} name="summary" maxLength={120} required disabled={busy||stale}/></label>
        <label>Connector source version<input defaultValue={preparation?.preview.source_version} name="source_version" maxLength={200} required disabled={busy||stale}/></label>
        <button disabled={busy||stale}>Validate and attach binding</button>
      </form></details>}
  </section>;
}
