"""Observe planned shutdown of the real lab API and deliver to a local HTTP receiver."""
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from uuid import uuid4

import httpx
from backend.config import ROOT
from scripts.readiness_monitor import check


def main():
    if os.environ.get('SALES_PHASE7_ACCEPTANCE') != 'enabled':
        raise SystemExit('Explicit lab switch required')
    folder=ROOT/'local/phase-7'/('alert-'+uuid4().hex[:12]);folder.mkdir()
    health='http://127.0.0.1:8044/health/ready'
    with httpx.Client(trust_env=False,timeout=3) as client:
        assert client.get(health).status_code==200, 'Actual lab API must initially be healthy'
    received=[];accept=False
    class Receiver(BaseHTTPRequestHandler):
        def do_POST(self):
            size=int(self.headers.get('Content-Length',0))
            if not 0<size<4096:
                self.send_response(413);self.end_headers();return
            body=json.loads(self.rfile.read(size))
            received.append({'key':self.headers.get('Idempotency-Key'),'event':body,'accepted':accept})
            self.send_response(204 if accept else 503);self.end_headers()
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Receiver)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    receiver=f'http://127.0.0.1:{server.server_port}/events'
    state=folder/'state.sqlite'
    try:
        assert check(state,health,receiver)=={'readiness':'healthy','delivered_this_check':0,'pending':0}
        deadline=time.monotonic()+1000
        while time.monotonic()<deadline:
            result=check(state,health,receiver)
            if result['readiness']=='unavailable':break
            time.sleep(5)
        else:raise RuntimeError('No actual lab API shutdown observed')
        assert result['pending']==1 and result['delivered_this_check']==0
        accept=True
        delivered=check(state,health,receiver)
        assert delivered['pending']==0 and delivered['delivered_this_check']==1
        assert len(received)==2 and received[0]['key']==received[1]['key']
        assert received[1]['accepted'] and received[1]['event']['type']=='readiness.unavailable'
        assert check(state,health,receiver)['delivered_this_check']==0
        report={'status':'passed','scope':'Actual API planned shutdown observed over HTTP; local receiver delivery',
                'initial_healthy':True,'failed_receiver_preserves_pending':True,
                'retry_event_id_stable':True,'accepted_receipts':1,'subsequent_check_no_duplicate':True,
                'limitations':['Local HTTP receiver only, not email/Slack or human acknowledgement',
                               'Planned application stop, not host reboot',
                               'Receiver failure deliberately injected via503','No recovery transition in this drill']}
        (folder/'result.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
    finally:
        server.shutdown();server.server_close();thread.join(timeout=5)


if __name__=='__main__':main()
