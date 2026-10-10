"""Validate browser wait intervals against actual native core receipts."""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
from backend.config import ROOT
from scripts.score_manual_review import score,stamp


def score_live(session,fixture_bytes,receipt_dir):
    adapted=copy.deepcopy(session)
    waits={};edits={}
    previous=stamp(session['started_utc'])
    for row in adapted['records']:
        wait=row['system_wait_seconds']
        if type(wait) not in {int,float} or not math.isfinite(wait) or wait<0:raise ValueError('Invalid wait duration')
        events=row.get('request_events',[]);receipt=row.get('server_receipt')
        if row['mode']=='manual':
            if wait!=0 or events or receipt is not None:raise ValueError('Manual row contains assistance')
        else:
            if len(events)!=2 or [e['type'] for e in events]!=['request','response']:raise ValueError('Invalid request events')
            start,end=[stamp(e['utc']) for e in events]
            if start<previous or end<start or abs((end-start).total_seconds()-wait)>0.5 or end>stamp(row['events'][0]['utc']):raise ValueError('Inconsistent waiting interval')
            # IDs must match frozen tasks before any path is constructed.
            valid={t['id'] for t in json.loads(fixture_bytes)['tasks']}
            if row['case_id'] not in valid:raise ValueError('Unknown case')
            from uuid import UUID
            sid=str(UUID(session['session_id']))
            path=Path(receipt_dir)/f"{sid}-{row['case_id']}.json"
            stored=json.loads(path.read_text())
            if stored!=receipt or receipt['session_id']!=sid or receipt['case_id']!=row['case_id'] or receipt['dataset_sha256']!=session['dataset_sha256']:raise ValueError('Server receipt mismatch')
            digest=hashlib.sha256(json.dumps({k:v for k,v in receipt.items() if k!='receipt_sha256'},sort_keys=True).encode()).hexdigest()
            if digest!=receipt['receipt_sha256']:raise ValueError('Receipt hash mismatch')
            if receipt['answer']!=row['initial_answer'] or receipt['core_seconds']<0 or receipt['core_seconds']>wait+0.5:raise ValueError('Receipt timing or answer mismatch')
        waits[row['case_id']]=wait
        values=dict(row['initial_answer']);revisions=0
        for event in row['events']:
            if event['type']=='field_change':
                field=event['field'];value=event['value']
                if field=='eligible':value={'true':True,'false':False,'':''}[value]
                if values.get(field)!='' and values.get(field)!=value:revisions+=1
                values[field]=value
        edits[row['case_id']]=revisions
        row['system_wait_seconds']=None
        previous=stamp(row['finished_utc'])
    report=score(adapted,fixture_bytes)
    for row in report['cases']:
        row['system_wait_seconds']=waits[row['case_id']];row['revisions_to_populated_fields']=edits[row['case_id']]
    for mode,group in report['groups'].items():
        group['system_wait_seconds']=sum(r['system_wait_seconds'] for r in report['cases'] if r['mode']==mode)
        group['revisions_to_populated_fields']=sum(r['revisions_to_populated_fields'] for r in report['cases'] if r['mode']==mode)
    report['scope']='Observed live local deterministic due-review worksheet; browser request waiting verified against native core receipts.'
    report['limitations']=['User attestation still required; receipt consistency does not prove human authorship.',
        'Repeated four-pair synthetic tasks, one operator; learning/carry-over possible. No live model, connected CRM or customer ROI claim.',
        'Active interval includes reading/page overhead. Field revisions are not automatically successful corrections.']
    return report


def main():
    p=argparse.ArgumentParser();p.add_argument('session',type=Path);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    raw=args.session.read_bytes();report=score_live(json.loads(raw),(ROOT/'fixtures/evaluation/manual-review-v1.json').read_bytes(),ROOT/'local/phase-6/live-manual')
    report['source_sha256']=hashlib.sha256(raw).hexdigest()
    with args.output.open('x') as f:json.dump(report,f,indent=2)
    print(json.dumps(report['groups']))


if __name__=='__main__':main()
