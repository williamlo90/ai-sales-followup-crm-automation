"""Validate observed worksheet data and score answers, without manufacturing observations."""
import argparse
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
from backend.config import ROOT


def stamp(value):
    result=datetime.fromisoformat(value)
    if result.tzinfo is None:raise ValueError('Aware timestamp required')
    return result


def score(session,fixture_bytes):
    fixture=json.loads(fixture_bytes);tasks=fixture['tasks']
    if session.get('completed') is not True:raise ValueError('Session incomplete')
    if session.get('dataset_sha256')!=hashlib.sha256(fixture_bytes).hexdigest():raise ValueError('Fixture hash mismatch')
    rows=session.get('records',[])
    if len(rows)!=len(tasks):raise ValueError('Wrong task count')
    previous=stamp(session['started_utc']);results=[]
    for row,task in zip(rows,tasks):
        if any(row.get(k)!=task[k] for k in ['pair','mode']) or row.get('case_id')!=task['id']:raise ValueError('Task order or mode mismatch')
        initial=task['expected'] if task['mode']=='assisted' else {'eligible':'','reason':''}
        if row['initial_answer']!=initial:raise ValueError('Initial answer mismatch')
        events=row['events']
        if not events or events[0]['type']!='start':raise ValueError('Missing start')
        started=stamp(events[0]['utc'])
        if started<previous:raise ValueError('Overlapping tasks')
        last=started;paused=False;active_s=0.;paused_s=0.;changes=0;answer=dict(initial)
        for event in events[1:]:
            now=stamp(event['utc'])
            if now<last:raise ValueError('Reversed event time')
            elapsed=(now-last).total_seconds()
            if paused:paused_s+=elapsed
            else:active_s+=elapsed
            last=now;kind=event['type']
            if kind=='pause' and not paused:paused=True
            elif kind=='resume' and paused:paused=False
            elif kind=='field_change' and not paused:
                field=event['field'];value=event['value']
                if field not in {'eligible','reason'}:raise ValueError('Unknown field')
                if field=='eligible':
                    if value not in {'true','false',''}:raise ValueError('Invalid eligibility')
                    value={'true':True,'false':False,'':''}[value]
                answer[field]=value;changes+=1
            else:raise ValueError('Invalid event transition')
        finished=stamp(row['finished_utc'])
        if paused or finished<last:raise ValueError('Invalid finish')
        active_s+=(finished-last).total_seconds();previous=finished
        for name,derived in [('active_seconds',active_s),('paused_seconds',paused_s)]:
            value=row[name]
            if type(value) not in {int,float} or not math.isfinite(value) or value<0 or abs(value-derived)>0.5:raise ValueError('Timing inconsistent')
        if type(row['field_changes']) is not int or row['field_changes']!=changes or row['submit_touches']!=1:raise ValueError('Interaction counts inconsistent')
        if row['system_wait_seconds'] is not None:raise ValueError('Cached assistance has no measured system wait')
        if row['answer']!=answer or type(answer['eligible']) is not bool or not answer['reason']:raise ValueError('Answer differs from observed changes')
        results.append({'case_id':task['id'],'pair':task['pair'],'mode':task['mode'],'correct':answer==task['expected'],
                        'active_seconds':row['active_seconds'],'paused_seconds':row['paused_seconds'],'field_changes':changes,
                        'submit_touches':1,'changed_assisted_answer':task['mode']=='assisted' and answer!=initial})
    if stamp(session['exported_utc'])<previous:raise ValueError('Export precedes finish')
    groups={mode:{'n':sum(r['mode']==mode for r in results),
                  'correct':sum(r['correct'] for r in results if r['mode']==mode),
                  'active_seconds':sum(r['active_seconds'] for r in results if r['mode']==mode),
                  'field_changes':sum(r['field_changes'] for r in results if r['mode']==mode),
                  'submit_touches':sum(r['submit_touches'] for r in results if r['mode']==mode)} for mode in ['manual','assisted']}
    return {'session_id':session['session_id'],'dataset_sha256':session['dataset_sha256'],'groups':groups,'cases':results,
            'scope':fixture['scope'],'limitations':['File consistency checks do not establish human authorship; operator confirmation required.',
            'Single operator, four pairs; learning/carry-over possible. Cached deterministic assistance, no live AI/CRM latency or ROI claim.',
            'Field edits are not necessarily corrections. Active interval includes reading and page overhead; system wait unmeasured.']}


def main():
    p=argparse.ArgumentParser();p.add_argument('session',type=Path);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    raw=args.session.read_bytes();result=score(json.loads(raw),(ROOT/'fixtures/evaluation/manual-review-v1.json').read_bytes())
    result['source_sha256']=hashlib.sha256(raw).hexdigest()
    with args.output.open('x',encoding='utf-8') as target:json.dump(result,target,indent=2)
    print(json.dumps(result['groups']))


if __name__=='__main__':main()
