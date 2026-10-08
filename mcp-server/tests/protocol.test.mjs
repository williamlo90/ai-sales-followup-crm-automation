import test from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {createInterface} from 'node:readline';
import {once} from 'node:events';
import http from 'node:http';
import {connectSales} from '../dist/client.js';

const root=fileURLToPath(new URL('../../',import.meta.url));
const unwrap=r=>r.structuredContent??JSON.parse(r.content[0].text);

test('real stdio client to native shared core: extraction, replay, scope, stale and disabled effects',async()=>{
  const process=spawn(fileURLToPath(new URL('../../.venv/Scripts/python.exe',import.meta.url)),['-m','scripts.mcp_fixture'],{cwd:root,stdio:['ignore','pipe','pipe']});
  const lines=createInterface({input:process.stdout});
  process.stderr.on('data',()=>{});
  const clients=[];
  try{
    const [line]=await Promise.race([once(lines,'line'),new Promise((_,reject)=>{const t=setTimeout(()=>reject(Error('fixture_start_timeout')),10000);t.unref();})]);
    const base=`http://127.0.0.1:${JSON.parse(line).port}`;
    for(let i=0;i<50;i++){try{if((await fetch(base+'/health/live')).ok)break;}catch{}await new Promise(r=>setTimeout(r,50));}
    const client=await connectSales(base,'test-operator');clients.push(client);
    assert.equal(client.getNegotiatedProtocolVersion(),'2026-07-28');
    const tools=await client.listTools();assert.equal(tools.tools.length,7);
    assert(!tools.tools.some(t=>t.name.includes('approve') && !t.name.includes('approved')));
    const call=(name,args)=>client.callTool({name:'sales.'+name,arguments:args});
    assert.equal(unwrap(await call('get_deal_context',{deal_id:'pilot'})).deal.account_id,'northstar');
    const extraction=unwrap(await call('extract_commitments',{deal_id:'pilot'}));
    assert.equal(extraction.result.trace.validation,'contract-double');
    assert.equal(extraction.result.extraction.commitments[0].owner,'Alice');
    const args={deal_id:'pilot',deal_version:1,commitment:{id:'c1',revision:1}};
    const prepared=unwrap(await call('prepare_crm_update',args)).result;
    assert.equal(unwrap(await call('prepare_crm_update',args)).result.id,prepared.id);
    assert.equal(unwrap(await call('draft_followup',{proposal_id:prepared.id})).result.send_enabled,false);
    for(const name of ['apply_crm_changes','send_approved_draft'])assert.equal(unwrap(await call(name,{proposal_id:prepared.id})).error,'execution_disabled');
    assert.equal((await call('prepare_crm_update',{...args,tenant_id:'other'})).isError,true);
    const foreign=await connectSales(base,'test-foreign');clients.push(foreign);
    assert.equal(unwrap(await foreign.callTool({name:'sales.get_deal_context',arguments:{deal_id:'pilot'}})).error,'record_not_found');
    const auditor=await connectSales(base,'test-auditor');clients.push(auditor);
    assert.equal(unwrap(await auditor.callTool({name:'sales.prepare_crm_update',arguments:args})).error,'role_not_permitted');
    assert.equal(unwrap(await call('reconcile_followup',{operation_id:'missing'})).error,'record_not_found');
    const changed=await fetch(base+'/v1/ingest/deals/pilot/sources',{method:'PUT',headers:{Authorization:'Bearer test-worker','Content-Type':'application/json'},
      body:JSON.stringify({external_id:'message',revision:2,occurred_at:'2026-10-09T01:00:00Z',text:'Cancel that commitment.'})});
    assert.equal(changed.status,200);
    assert.equal(unwrap(await call('draft_followup',{proposal_id:prepared.id})).error,'source_changed');
  }finally{for(const client of clients)await client.close();lines.close();process.kill();await once(process,'exit');}
});

test('stdio cancellation, bounded response and sanitized failures',async()=>{
  let mode='large';let received;
  const server=http.createServer(async(req,res)=>{
    received?.();
    if(mode==='delay'){await new Promise(r=>setTimeout(r,300));if(res.destroyed)return;}
    res.setHeader('Content-Type','application/json');
    if(mode==='large')return res.end(JSON.stringify({text:'x'.repeat(300000)}));
    res.statusCode=500;res.end(JSON.stringify({error:'secret-never-echo'}));
  });
  await new Promise(r=>server.listen(0,'127.0.0.1',r));
  const client=await connectSales(`http://127.0.0.1:${server.address().port}`,'synthetic-token');
  const args={name:'sales.get_deal_context',arguments:{deal_id:'pilot'}};
  try{
    assert.equal(unwrap(await client.callTool(args)).error,'response_too_large');
    mode='error';assert.equal(unwrap(await client.callTool(args)).error,'domain_rejected');
    mode='delay';const controller=new AbortController();
    const arrived=new Promise(r=>received=r);
    const pending=client.callTool(args,{signal:controller.signal});
    await arrived;controller.abort();await assert.rejects(pending);
    await new Promise(r=>setTimeout(r,100));
    mode='error';assert.equal(unwrap(await client.callTool(args)).error,'domain_rejected');
  }finally{await client.close();server.closeAllConnections();await new Promise(r=>server.close(r));}
});
