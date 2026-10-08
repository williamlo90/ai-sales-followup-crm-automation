import {McpServer,fromJsonSchema} from '@modelcontextprotocol/server';
import {serveStdio} from '@modelcontextprotocol/server/stdio';
import {readFileSync} from 'node:fs';

const schema=(skill:string,kind:string)=>JSON.parse(readFileSync(new URL(`../../skills/${skill}/${kind}.schema.json`,import.meta.url),'utf8'));
const shared=(name:string)=>JSON.parse(readFileSync(new URL(`../schemas/${name}.json`,import.meta.url),'utf8'));
const id={type:'string',minLength:1,maxLength:200};
const object=(properties:Record<string,unknown>)=>({type:'object',properties,required:Object.keys(properties),additionalProperties:false});
type Spec={name:string;input:any;output?:any;path:(a:any)=>string;method?:string;body?:(a:any)=>unknown;readOnly:boolean};
const skills=['extract_commitments','prepare_crm_update','draft_followup','reconcile_followup'];
const specs:Spec[]=skills.map(skill=>({name:`sales.${skill}`,input:schema(skill,'input'),output:schema(skill,'output'),
  path:()=>`/v1/skills/${skill}`,method:'POST',body:a=>a,readOnly:skill==='draft_followup'}));
specs.push({name:'sales.get_deal_context',input:object({deal_id:id}),output:shared('context'),path:a=>`/v1/deals/${encodeURIComponent(a.deal_id)}/context`,readOnly:true});
for(const [name,kind] of [['apply_crm_changes','crm'],['send_approved_draft','email']])
  specs.push({name:`sales.${name}`,input:object({proposal_id:id}),output:shared('operation'),path:a=>`/v1/proposals/${encodeURIComponent(a.proposal_id)}/execute/${kind}`,method:'POST',readOnly:false});
const errors=new Set(['record_not_found','role_not_permitted','invalid_session','authentication_required','source_changed','stale_proposal',
  'commitment_changed','commitment_cancelled','proposal_expired','execution_disabled','send_not_permitted','approval_required',
  'model_not_configured','model_call_budget_exhausted','proposal_already_owned','customer_opted_out','context_changed','skill_output_invalid',
  'effect_overlap_requires_review','revision_update_requires_review']);
class Failure extends Error {}

function buildServer(){
  const base=new URL(process.env.SALES_API_URL ?? 'http://127.0.0.1:8040');
  if(base.protocol!=='http:' || !['127.0.0.1','localhost'].includes(base.hostname) || base.username || base.password || base.pathname!=='/' || base.search || base.hash)throw new Failure('invalid_api_url');
  const token=process.env.SALES_TOKEN;
  if(!token || token.length>256 || /\s/.test(token))throw new Failure('invalid_session');
  const server=new McpServer({name:'sales-followup',version:'0.1.0'});
  let active=false;
  for(const spec of specs){
    const validator=spec.output ? fromJsonSchema<any>(spec.output) : undefined;
    server.registerTool(spec.name,{description:spec.name+'; server-enforced scope and approvals. External execution is disabled unless explicitly configured.',
      inputSchema:fromJsonSchema<any>(spec.input),...(validator?{outputSchema:validator}:{}),
      annotations:{readOnlyHint:spec.readOnly,destructiveHint:!spec.readOnly,idempotentHint:spec.readOnly,openWorldHint:!spec.readOnly}},async(args,ctx)=>{
      if(active)return {isError:true,content:[{type:'text' as const,text:'{"error":"request_limit"}'}]};
      active=true;
      try{
        const response=await fetch(new URL(spec.path(args),base),{method:spec.method??'GET',redirect:'error',
          headers:{Authorization:`Bearer ${token}`,'Content-Type':'application/json'},
          body:spec.body?JSON.stringify(spec.body(args)):undefined,signal:AbortSignal.any([ctx.mcpReq.signal,AbortSignal.timeout(65000)])});
        const chunks:Uint8Array[]=[];let size=0;
        if(response.body){for await(const chunk of response.body){size+=chunk.length;if(size>262144)throw new Failure('response_too_large');chunks.push(chunk);}}
        const data=JSON.parse(Buffer.concat(chunks).toString('utf8'));
        if(!response.ok)throw new Failure(errors.has(data?.error)?data.error:response.status>=500 && !spec.readOnly?'outcome_unknown':'domain_rejected');
        if(validator && (await validator['~standard'].validate(data)).issues)throw new Failure('domain_response_invalid');
        return {structuredContent:data,content:[{type:'text' as const,text:JSON.stringify(data)}]};
      }catch(error){
        const code=error instanceof Failure?error.message:ctx.mcpReq.signal.aborted?'request_cancelled':spec.readOnly?'domain_unavailable':'outcome_unknown';
        return {isError:true,content:[{type:'text' as const,text:JSON.stringify({error:code})}]};
      }finally{active=false;}
    });
  }
  return server;
}
try{serveStdio(buildServer);}catch{console.error('mcp_startup_failed');process.exitCode=1;}
