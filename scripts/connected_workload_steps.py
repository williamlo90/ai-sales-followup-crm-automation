"""Bounded connected workload. All transitions use the deployed shared API."""
import json
import math
import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx


def percentile(values, p):
    return sorted(values)[max(0, math.ceil(len(values)*p)-1)]


def run(http, call, cfg, folder, *, profiles=None, after_enqueue=None, profile_deadline_seconds=360):
    profiles = profiles or [('normal', 2, None), ('peak', 3, 0), ('short_soak', 4, 30)]
    results = []
    # Freeze the source set before review. New thread evidence intentionally
    # invalidates approvals, which is a separate streaming/freshness scenario.
    fixtures = []
    for _ in range(sum(count for _, count, _ in profiles)):
        ident = 'load-'+uuid4().hex
        instant = datetime.now(timezone.utc)
        source = 'Please confirm synthetic demo '+ident+'.'
        call(http, 'PUT', '/v1/ingest/deals/connected-demo/sources', body={
            'external_id':ident, 'revision':1,
            'occurred_at':instant.isoformat(), 'text':source})
        fixtures.append((ident, instant, source))
    fixture_index = 0
    for name, count, spacing in profiles:
        started = time.monotonic()
        pending = {}
        finished = []
        launched = 0
        maximum_backlog = 0
        deadline = started+profile_deadline_seconds
        while len(finished) < count:
            now = time.monotonic()
            if now > deadline:
                raise RuntimeError('workload_deadline_'+name)
            should_launch = (not pending if spacing is None else now-started >= launched*spacing)
            if launched < count and should_launch:
                ident, instant, source = fixtures[fixture_index]
                fixture_index += 1
                call(http, 'POST', '/v1/deals/connected-demo/commitments', role='operator', body={
                    'id':ident, 'revision':1, 'owner':'Sales',
                    'description':'Project04 workload '+ident,
                    'due_at':(instant+timedelta(days=1)).isoformat(),
                    'observed_at':instant.isoformat(),
                    'evidence':{'source_id':ident,'revision':1,'quote':source}})
                payload = {'deal_id':'connected-demo','deal_version':1,'journey':'intake',
                           'kind':'crm','commitment':{'id':ident,'revision':1}}
                queued_at = time.monotonic()
                job = call(http,'POST','/v1/workflows/jobs',body=payload,status=201)
                replay = call(http,'POST','/v1/workflows/jobs',body=payload,status=201)
                assert replay['id'] == job['id']
                if after_enqueue:after_enqueue(job)
                pending[job['id']] = {'enqueued':queued_at,'approved':False}
                launched += 1
            maximum_backlog = max(maximum_backlog,len(pending))
            for ident, sample in list(pending.items()):
                job = call(http,'GET','/v1/workflows/jobs/'+ident)
                if job['status'] in {'review','unknown','disabled'}:
                    (folder/'workload-failure.json').write_text(json.dumps({
                        'profile':name,'status':job['status'],'error_code':job.get('error_code'),
                        'completed_profiles':results,'completed_in_profile':finished,
                        'launched':launched,'backlog':len(pending)},indent=2))
                    raise RuntimeError('workload_terminal_'+str(job.get('error_code')))
                if job['proposal_id'] and not sample['approved']:
                    sample['queue_wait_seconds'] = time.monotonic()-sample['enqueued']
                    proposal = call(http,'GET','/v1/proposals/'+job['proposal_id'],role='operator')
                    preview = call(http,'GET','/v1/proposals/'+proposal['id']+'/connector-preparation',role='operator')['preview']
                    with httpx.Client(base_url=cfg['base_url'],trust_env=False,timeout=25) as remote:
                        response=remote.post('/v1/activities/prepare',headers={'Authorization':'Bearer '+cfg['operator_token']},json={k:preview[k] for k in ('opportunity_id','assignee_id','due_date','summary')})
                        assert response.status_code==201
                        prepared=response.json()
                        response=remote.post('/v1/proposals/'+prepared['id']+'/approve',headers={'Authorization':'Bearer '+cfg['approver_token']},json={'payload_hash':prepared['payload_hash']})
                        assert response.status_code==201
                        approval=response.json()
                    call(http,'POST','/v1/proposals/'+proposal['id']+'/connector-binding',role='operator',body={
                        'connector_tenant':cfg['tenant'],'proposal_id':prepared['id'],
                        'approval_id':approval['id'],'actor_id':prepared['actor_id'],'preview':prepared['preview']})
                    call(http,'POST','/v1/proposals/'+proposal['id']+'/approvals',role='approver',body={'kind':'crm','payload_hash':proposal['payload_hash']})
                    sample['approved'] = True
                if job['status']=='completed':
                    operation=call(http,'GET','/v1/operations/'+job['operation_id'])
                    assert operation['status']=='verified'
                    operations=call(http,'GET','/v1/proposals/'+job['proposal_id']+'/operations')['items']
                    assert len(operations)==1
                    finished.append({'verified_seconds':time.monotonic()-sample['enqueued'],
                                     'queue_wait_seconds':sample['queue_wait_seconds']})
                    del pending[ident]
            (folder/'workload-progress.json').write_text(json.dumps({
                'profile':name,'launched':launched,'verified':len(finished),'backlog':len(pending),
                'elapsed_seconds':round(time.monotonic()-started,2)}))
            time.sleep(1)
        elapsed=time.monotonic()-started
        values=[s['verified_seconds'] for s in finished]
        results.append({'profile':name,'n':count,'elapsed_seconds':elapsed,
                        'throughput_per_minute':count*60/elapsed,'maximum_backlog':maximum_backlog,
                        'p50_seconds':percentile(values,.5),'p90_seconds':percentile(values,.9),
                        'p95_seconds':percentile(values,.95),'samples':finished,
                        'errors':0,'verified_operations':count})
        (folder/'workload-results.json').write_text(json.dumps(results,indent=2))
    return {'status':'passed','profiles':results,'emails_sent':0,'paid_model_calls':0,
            'scheduler_interval_seconds':10,'review':'automated separate lab roles',
            'limitations':['Seeded deterministic input; Graph/model performance excluded',
                           'Accelerated 10-second lab cadence, not production five-minute latency',
                           'Small N: p90/p95 are descriptive near-maximum samples',
                           'Short soak only; no long-duration reliability claim']}
