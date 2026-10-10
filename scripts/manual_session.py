"""Human-operated timing recorder; never generates benchmark results itself."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time


class Recorder:
    def __init__(self, clock=time.monotonic):
        self.clock=clock; self.started=clock(); self.previous=self.started
        self.mode='active'; self.active=0.; self.waiting=0.; self.touches=0; self.corrections=0
        self.events=[]; self.complete=False

    def event(self, action):
        if self.complete:raise ValueError('Session already ended')
        if action not in {'touch','correction','wait','work','done','abort'}:raise ValueError('Unknown event')
        if action=='wait' and self.mode=='waiting':raise ValueError('Already waiting')
        if action=='work' and self.mode=='active':raise ValueError('Already working')
        now=self.clock()
        if now<self.previous:raise ValueError('Clock moved backwards')
        if self.mode=='active':self.active+=now-self.previous
        else:self.waiting+=now-self.previous
        self.previous=now
        self.events.append({'action':action,'elapsed_seconds':now-self.started,'observed_utc':datetime.now(timezone.utc).isoformat()})
        if action=='touch':self.touches+=1
        if action=='correction':self.corrections+=1
        if action=='wait':self.mode='waiting'
        if action=='work':self.mode='active'
        if action in {'done','abort'}:self.complete=True
        return self.snapshot(action=='done')

    def snapshot(self, completed=False):
        return {'completed':completed,'active_seconds':self.active,'waiting_seconds':self.waiting,
                'touches':self.touches,'corrections':self.corrections,'events':self.events,
                'correctness':'unreviewed','measurement_scope':'human-marked intervals; recorder interaction overhead included; no ROI claim'}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--operator',required=True);p.add_argument('--case',required=True)
    p.add_argument('--mode',choices=['manual','assisted'],required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--answer',type=Path,required=True)
    args=p.parse_args()
    if args.answer.resolve()==args.output.resolve():raise ValueError('Answer and timing files must differ')
    # Exclusive reservation prevents overwriting any observed session.
    with args.output.open('x',encoding='utf-8') as output:
        meta={'operator':args.operator,'case_id':args.case,'mode':args.mode,'started_utc':None}
        recorder=None;result={'completed':False,'reason':'not_started'}
        try:
            input('Prepare task and answer editor, then Enter to start. ')
            meta['started_utc']=datetime.now(timezone.utc).isoformat();recorder=Recorder()
            print('Commands: touch, correction, wait, work, done, abort. Mark each actual operation; no invented counts.')
            while True:
                action=input('event> ').strip()
                if action=='done' and not args.answer.is_file():
                    print('Save the actual answer file before finishing.');continue
                try:result=recorder.event(action)
                except ValueError as exc:print(str(exc));continue
                output.seek(0);json.dump({**meta,**result},output,indent=2);output.truncate();output.flush()
                if action in {'done','abort'}:break
            if result['completed']:
                result['answer_path']=str(args.answer.resolve())
                result['answer_sha256']=hashlib.sha256(args.answer.read_bytes()).hexdigest()
        except (EOFError,KeyboardInterrupt):
            result=recorder.event('abort') if recorder and not recorder.complete else result
        finally:
            output.seek(0);json.dump({**meta,**result},output,indent=2);output.truncate();output.flush()


if __name__=='__main__':main()
