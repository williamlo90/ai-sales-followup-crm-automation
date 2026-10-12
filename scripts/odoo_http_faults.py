"""Bounded real-TCP fault injection in front of the project-owned Odoo sandbox."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
from backend.read_clients import BoundedReader, ReadError


def check(cfg):
    state={'mode':'recover','requests':0,'forwarded':0}
    class Proxy(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path!='/v1/opportunities':
                self.send_response(404);self.end_headers();return
            state['requests']+=1
            throttle=state['mode']!='recover' or state['requests']<=2
            if throttle:
                self.send_response(429)
                self.send_header('Retry-After','11' if state['mode']=='long' else '0')
                self.send_header('Content-Length','2');self.end_headers();self.wfile.write(b'{}')
                return
            with httpx.Client(trust_env=False,timeout=20) as client:
                response=client.get(cfg['base_url']+'/v1/opportunities',headers={
                    'Authorization':self.headers.get('Authorization','')})
            state['forwarded']+=1
            self.send_response(response.status_code)
            self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(response.content)))
            self.end_headers();self.wfile.write(response.content)
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Proxy)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    endpoint=f'http://127.0.0.1:{server.server_port}/v1/opportunities'
    reader=BoundedReader(lambda:cfg['operator_token'])
    checks=[]
    try:
        reader.get(endpoint)
        assert state['requests']==3 and state['forwarded']==1
        checks.append('tcp_two_injected_429_then_actual_odoo_read_recovers')
        for mode,count,wait in [('persistent',3,0),('long',1,11)]:
            state.update(mode=mode,requests=0,forwarded=0)
            try:reader.get(endpoint)
            except ReadError as error:assert error.code=='retry_later' and error.retry_after==wait
            else:raise AssertionError('Rate-limited read accepted')
            assert state['requests']==count and state['forwarded']==0
            checks.append('tcp_'+mode+'_429_bounded_no_upstream_call')
    finally:
        server.shutdown();server.server_close();thread.join(timeout=5)
    return checks
