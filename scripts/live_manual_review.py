"""Loopback-only live decision worksheet. Calls shared rules, never model/email/CRM."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import secrets
from threading import Lock
import time
from uuid import UUID
from fastapi import FastAPI,Request,HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from backend.config import ROOT
from backend.sales_rules import due_eligibility


class Session(BaseModel):
    session_id: UUID


def create_app(output_dir=None):
    raw=(ROOT/'fixtures/evaluation/manual-review-v1.json').read_bytes();fixture=json.loads(raw)
    tasks={task['id']:task for task in fixture['tasks']}
    key=secrets.token_urlsafe(24);gate=Lock()
    folder=Path(output_dir or ROOT/'local/phase-6/live-manual');folder.mkdir(parents=True,exist_ok=True)
    app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None)
    app.state.test_key=key
    @app.middleware('http')
    async def loopback(request,call_next):
        if request.headers.get('host')!='127.0.0.1:8046':
            from fastapi.responses import JSONResponse
            return JSONResponse({'error':'invalid_host'},status_code=403)
        return await call_next(request)
    @app.get('/',response_class=HTMLResponse)
    def page():
        pack={'hash':hashlib.sha256(raw).hexdigest(),'scope':'Live local due-review worksheet; shared deterministic core; no model or connected effects.',
              'tasks':[{k:v for k,v in task.items() if k!='expected'}|{'suggestion':None} for task in tasks.values()]}
        template=(ROOT/'scripts/manual_review.html').read_text(encoding='utf-8')
        template=template.replace('Assisted memakai saran core yang sudah dihitung; tidak mengukur waktu tunggu AI.','Assisted meminta saran core lokal saat tugas dimulai. Waktu tunggu request dicatat terpisah; tidak ada API model atau CRM.')
        template=template.replace('const pack=__PACK__','const accessKey='+json.dumps(key)+'; const pack='+json.dumps(pack))
        template=template.replace('initial;','initial,waitSeconds=0,requestEvents=[],serverReceipt=null;')
        template=template.replace('active=true;paused=false;work=breaks=changes=0','active=false;paused=false;work=breaks=changes=0')
        template=template.replace("$('begin').onclick=()=>{","$('begin').onclick=async()=>{")
        template=template.replace("initial=t.suggestion||{eligible:'',reason:''};", """waitSeconds=0;requestEvents=[];serverReceipt=null;
$('begin').disabled=true;initial={eligible:'',reason:''};
if(t.mode==='assisted'){
 $('state').textContent='Menunggu core lokal...';const requestStart=performance.now();const started=new Date().toISOString();
 try{
  const response=await fetch('/assist/'+t.id,{method:'POST',headers:{'Content-Type':'application/json','X-Worksheet-Key':accessKey},body:JSON.stringify({session_id:session.session_id})});
  if(!response.ok)throw Error('HTTP '+response.status);
  serverReceipt=await response.json();initial=serverReceipt.answer;
  waitSeconds=(performance.now()-requestStart)/1000;
  requestEvents=[{type:'request',utc:started},{type:'response',utc:new Date().toISOString()}];
 }catch(error){active=false;$('message').textContent='Request gagal. Jangan ulang otomatis; simpan detail dan hubungi agent. '+error.message;return;}
}
active=true;last=performance.now();""")
        template=template.replace('system_wait_seconds:null','system_wait_seconds:waitSeconds,request_events:requestEvents,server_receipt:serverReceipt')
        template=template.replace("events.push({type:'start',utc:new Date().toISOString()});state();", "events.push({type:'start',utc:new Date().toISOString()});if(document.hidden)pause();else state();")
        template=template.replace("'sales-manual-session-'","'sales-live-manual-session-'")
        return HTMLResponse(template,headers={'Cache-Control':'no-store','Content-Security-Policy':"default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'"})
    @app.post('/assist/{case_id}')
    def assist(case_id:str,session:Session,request:Request):
        if request.headers.get('x-worksheet-key')!=key:raise HTTPException(403,'Invalid worksheet key')
        if request.headers.get('origin') not in {None,'http://127.0.0.1:8046'}:raise HTTPException(403,'Invalid origin')
        task=tasks.get(case_id)
        if task is None or task['mode']!='assisted':raise HTTPException(404,'Not an assisted task')
        if not gate.acquire(blocking=False):raise HTTPException(409,'Request already active')
        try:
            target=folder/f'{session.session_id}-{case_id}.json'
            if target.exists():raise HTTPException(409,'Case already measured for this session')
            started=time.perf_counter()
            args={k:datetime.fromisoformat(v) if k in {'due_at','now','source_at','last_contact'} and v else v for k,v in task['input'].items()}
            answer=due_eligibility(**args)
            record={'session_id':str(session.session_id),'case_id':case_id,'dataset_sha256':hashlib.sha256(raw).hexdigest(),'answer':answer,'core_seconds':time.perf_counter()-started}
            record['receipt_sha256']=hashlib.sha256(json.dumps(record,sort_keys=True).encode()).hexdigest()
            with target.open('x') as out:json.dump(record,out,indent=2)
            return record
        finally:gate.release()
    return app


if __name__=='__main__':
    import uvicorn
    uvicorn.run(create_app(),host='127.0.0.1',port=8046,log_level='warning')
