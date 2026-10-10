import copy
from datetime import datetime,timedelta,timezone
import hashlib,json
from pathlib import Path
import pytest
from scripts.score_manual_review import score


def fixture():
    raw=(Path(__file__).parents[1]/'fixtures/evaluation/manual-review-v1.json').read_bytes()
    tasks=json.loads(raw)['tasks'];start=datetime(2026,10,10,tzinfo=timezone.utc)
    session={'completed':True,'session_id':'automated-test-only','dataset_sha256':hashlib.sha256(raw).hexdigest(),'started_utc':start.isoformat(),'records':[]}
    for i,t in enumerate(tasks):
        now=start+timedelta(seconds=10*i);initial=t['expected'] if t['mode']=='assisted' else {'eligible':'','reason':''}
        events=[{'type':'start','utc':now.isoformat()}]
        if t['mode']=='manual':
            events += [{'type':'field_change','field':k,'value':str(v).lower() if isinstance(v,bool) else v,'utc':(now+timedelta(seconds=1)).isoformat()} for k,v in t['expected'].items()]
        session['records'].append({'case_id':t['id'],'pair':t['pair'],'mode':t['mode'],'initial_answer':initial,'answer':t['expected'],
            'events':events,'finished_utc':(now+timedelta(seconds=5)).isoformat(),'active_seconds':5,'paused_seconds':0,'field_changes':len(events)-1,'submit_touches':1,'system_wait_seconds':None})
    session['exported_utc']=(start+timedelta(seconds=80)).isoformat()
    return session,raw


def test_consistent_test_data_scored_without_human_claim():
    session,raw=fixture();result=score(session,raw)
    assert result['groups']['manual']['correct']==4
    assert result['groups']['assisted']['active_seconds']==20
    assert 'human authorship' in result['limitations'][0]


@pytest.mark.parametrize('change',['hash','duplicate','time','answer','incomplete','wait','initial'])
def test_inconsistent_observation_rejected(change):
    s,raw=fixture();s=copy.deepcopy(s)
    if change=='hash':s['dataset_sha256']='bad'
    if change=='duplicate':s['records'][1]=s['records'][0]
    if change=='time':s['records'][0]['active_seconds']=-1
    if change=='answer':s['records'][0]['answer']['eligible']=False
    if change=='incomplete':s['completed']=False
    if change=='wait':s['records'][0]['system_wait_seconds']=1
    if change=='initial':s['records'][0]['initial_answer']['eligible']=True
    with pytest.raises(ValueError):score(s,raw)
