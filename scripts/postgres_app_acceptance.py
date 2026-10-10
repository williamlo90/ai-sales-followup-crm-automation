"""FastAPI/shared-core acceptance against real PostgreSQL; no external effects."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from tempfile import TemporaryDirectory
from uuid import uuid4
from fastapi.testclient import TestClient
from backend.app import from_environment


def restart_owned_container(container):
    data = json.loads(subprocess.check_output(['docker','inspect',container],text=True,timeout=5))[0]
    if (data['Id'] != container or data['Config']['Labels'].get('sales.phase7.owner') != 'pg256-acceptance'
            or data['HostConfig']['Memory'] != 268435456):
        raise ValueError('Not the exact owned256MiB test container')
    subprocess.run(['docker','restart','--time','5',container],check=True,capture_output=True,timeout=15)
    deadline = time.monotonic()+15
    while time.monotonic()<deadline:
        result = subprocess.run(['docker','exec',container,'pg_isready','-U','sales_lab_owner','-d','sales_phase7_acceptance'],capture_output=True,timeout=3)
        if result.returncode == 0:return
        time.sleep(.25)
    raise RuntimeError('Restart readiness deadline')


def check_application(owner, dsn, tenants, restart_container=None):
    actors = {}; identities = {}
    for role in ('worker','operator','approver','auditor','outsider'):
        tenant = tenants[1] if role == 'outsider' else tenants[0]
        data = {'id':str(uuid4()),'tenant_id':str(tenant),'role':'auditor' if role=='outsider' else role,'deal_ids':['app-deal']}
        actors[role] = data
        identities[hashlib.sha256(role.encode()).hexdigest()] = data
        owner.execute('INSERT INTO actors(tenant_id,id,role) VALUES(%s,%s,%s)', (tenant,data['id'],data['role']))
    headers = lambda role: {'Authorization':'Bearer '+role}
    passed = []
    with TemporaryDirectory(prefix='sales-app-pg-') as directory:
        identity_path = Path(directory)/'identities.json'; identity_path.write_text(json.dumps(identities))
        changes = {'SALES_IDENTITIES_PATH':str(identity_path), 'SALES_STORAGE':'postgresql',
                   'SALES_POSTGRES_DSN':dsn, 'SALES_MODEL_ENABLED':'false'}
        previous = {k:os.environ.get(k) for k in changes}
        os.environ.update(changes)
        try:
            app = from_environment()
            with TestClient(app) as client:
                assert client.get('/health/ready').json()['storage'] == 'postgresql'
                now = datetime.now(timezone.utc)
                deal = {'account_id':'account-test','title':'Test deal','recipient':'recipient@example.test','version':1}
                source = {'external_id':'app-source','revision':1,'occurred_at':(now-timedelta(hours=1)).isoformat(),'text':'Morgan will deliver the checklist.'}
                response = client.put('/v1/ingest/deals/app-deal',headers=headers('worker'),json=deal)
                assert response.status_code == 200, response.text
                response = client.put('/v1/ingest/deals/app-deal/sources',headers=headers('worker'),json=source)
                assert response.status_code == 200, response.text
                proposal = {'deal_id':'app-deal','deal_version':1,'summary':'Checklist',
                    'due_at':(now+timedelta(days=1)).isoformat(),'draft':'Please confirm the checklist.',
                    'evidence':[{'source_id':'app-source','revision':1,'quote':source['text']}]}
                def prepare(_):
                    result = client.post('/v1/proposals',headers=headers('operator'),json=proposal)
                    assert result.status_code == 201, result.text
                    return result.json()
                with ThreadPoolExecutor(max_workers=4) as pool:
                    results = list(pool.map(prepare,range(8)))
                p = results[0]
                assert len({r['id'] for r in results}) == 1
                assert owner.execute("SELECT count(*) FROM proposals WHERE tenant_id=%s",(tenants[0],)).fetchone()[0] == 1
                assert owner.execute("SELECT count(*) FROM audit_events WHERE tenant_id=%s AND action='proposal.prepared'",(tenants[0],)).fetchone()[0] == 1
                passed.append('app_concurrent_prepare_8_requests_one_proposal_and_audit')
                def approve(_):
                    result = client.post(f"/v1/proposals/{p['id']}/approvals",headers=headers('approver'),json={'kind':'crm','payload_hash':p['payload_hash']})
                    assert result.status_code == 200, result.text
                    return result.json()
                with ThreadPoolExecutor(max_workers=4) as pool:
                    approvals = list(pool.map(approve,range(8)))
                assert all([a['kind'] for a in r['approvals']]==['crm'] for r in approvals)
                assert owner.execute("SELECT count(*) FROM approvals WHERE tenant_id=%s",(tenants[0],)).fetchone()[0] == 1
                assert owner.execute("SELECT count(*) FROM audit_events WHERE tenant_id=%s AND action='approval.crm'",(tenants[0],)).fetchone()[0] == 1
                passed.append('app_concurrent_approval_8_requests_one_approval_and_audit')
                assert client.post(f"/v1/proposals/{p['id']}/approvals",headers=headers('operator'),json={'kind':'email','payload_hash':p['payload_hash']}).status_code == 403
                assert client.get(f"/v1/proposals/{p['id']}",headers=headers('outsider')).status_code == 404
                passed.append('app_role_and_tenant_access_denied')
                # A fresh interpreter reconstructs the app using the same runtime
                # DSN/identities. This proves process restart, not server reboot.
                code = "from backend.app import from_environment; from fastapi.testclient import TestClient; import sys; c=TestClient(from_environment()); r=c.get('/v1/proposals/'+sys.argv[1],headers={'Authorization':'Bearer auditor'}); assert r.status_code==200; d=r.json(); assert d['approval_valid'] and [a['kind'] for a in d['approvals']]==['crm']; print('persisted')"
                result = subprocess.run([sys.executable,'-c',code,p['id']],capture_output=True,text=True,timeout=15)
                assert result.returncode == 0, 'Fresh-process read failed'
                passed.append('app_fresh_process_persistence_separate_crm_approval')
                # Exercise the actual persistent coordinator with effects disabled.
                commitment = {'id':'workflow-commitment','revision':1,'owner':'Morgan','description':'Deliver checklist',
                    'due_at':(now-timedelta(minutes=1)).isoformat(),'observed_at':source['occurred_at'],
                    'evidence':{'source_id':'app-source','revision':1,'quote':source['text']}}
                r = client.post('/v1/deals/app-deal/commitments',headers=headers('operator'),json=commitment)
                assert r.status_code == 200, r.text
                job_data = {'journey':'intake','kind':'crm','deal_id':'app-deal','deal_version':1,'commitment':{'id':commitment['id'],'revision':1}}
                r = client.post('/v1/workflows/jobs',headers=headers('worker'),json=job_data)
                assert r.status_code == 201,r.text
                job = r.json()
                assert client.post('/v1/workflows/jobs',headers=headers('worker'),json=job_data).json()['id'] == job['id']
                def tick(_):
                    r = client.post('/v1/workflows/intake/tick',headers=headers('worker'))
                    assert r.status_code == 200,r.text
                    return r.json()
                with ThreadPoolExecutor(max_workers=2) as pool:
                    ticks = list(pool.map(tick,range(2)))
                assert sorted(r['status'] for r in ticks) == ['awaiting_approval','idle']
                waiting = client.get('/v1/workflows/jobs/'+job['id'],headers=headers('worker')).json()
                assert waiting['status'] == 'awaiting_approval'
                assert owner.execute('SELECT lease_id FROM workflow_jobs WHERE tenant_id=%s AND id=%s',(tenants[0],job['id'])).fetchone()[0] is None
                passed.append('workflow_duplicate_enqueue_and_concurrent_ticks_one_claim')
                due = client.post('/v1/workflows/due/tick',headers=headers('worker'))
                assert due.status_code == 200,due.text
                due_job = due.json()
                assert due_job['status'] == 'awaiting_approval' and due_job['proposal_id'] == waiting['proposal_id']
                again = client.post('/v1/workflows/due/tick',headers=headers('worker'))
                assert again.status_code == 200 and again.json()['status'] == 'idle'
                assert owner.execute('SELECT count(*) FROM workflow_jobs WHERE tenant_id=%s',(tenants[0],)).fetchone()[0] == 2
                passed.append('due_discovery_cursor_replay_no_duplicate_job_or_proposal')
                wp = client.get('/v1/proposals/'+waiting['proposal_id'],headers=headers('approver')).json()
                assert client.post('/v1/proposals/'+wp['id']+'/approvals',headers=headers('approver'),json={'kind':'crm','payload_hash':wp['payload_hash']}).status_code == 200
                if restart_container:
                    started = owner.execute('SELECT pg_postmaster_start_time()').fetchone()[0]
                    owner.close()
                    restart_owned_container(restart_container)
                    import psycopg
                    with psycopg.connect(dsn,autocommit=True) as fresh:
                        assert fresh.execute('SELECT pg_postmaster_start_time()').fetchone()[0] > started
                    saved = client.get('/v1/proposals/'+wp['id'],headers=headers('auditor')).json()
                    saved_job = client.get('/v1/workflows/jobs/'+job['id'],headers=headers('worker')).json()
                    assert saved['approval_valid'] and [a['kind'] for a in saved['approvals']] == ['crm']
                    assert saved_job == waiting
                    from backend.postgres_store import PostgresStore
                    from backend.models import Actor
                    with PostgresStore(dsn).connect(Actor.model_validate(actors['auditor'])) as conn:
                        assert conn.execute('SELECT lease_id FROM workflow_jobs WHERE tenant=? AND id=?',(str(tenants[0]),job['id'])).fetchone()[0] is None
                    persisted_due = client.get('/v1/workflows/jobs/'+due_job['id'],headers=headers('worker')).json()
                    assert persisted_due['status'] == 'awaiting_approval' and persisted_due['proposal_id'] == waiting['proposal_id']
                    assert tick(None)['status'] == 'idle'
                    passed.append('real_database_restart_preserves_approval_job_schedule_and_lease')
                source['revision'] = 2; source['text'] = 'Morgan cancelled the checklist.'
                assert client.put('/v1/ingest/deals/app-deal/sources',headers=headers('worker'),json=source).status_code == 200
                stale = client.get(f"/v1/proposals/{p['id']}",headers=headers('auditor')).json()
                assert stale['validation_error'] == 'source_changed' and stale['approval_valid'] is False
                assert client.post(f"/v1/proposals/{p['id']}/approvals",headers=headers('approver'),json={'kind':'email','payload_hash':p['payload_hash']}).status_code == 409
                passed.append('app_source_revision_invalidates_approval')
                from backend.postgres_store import PostgresStore
                from backend.models import Actor
                with PostgresStore(dsn).connect(Actor.model_validate(actors['auditor'])) as conn:
                    assert conn.execute('SELECT count(*) FROM operations').fetchone()[0] == 0
                passed.append('app_no_external_operations')
                from scripts.postgres_boundary_acceptance import check_boundaries
                passed.extend(check_boundaries(dsn,actors))
        finally:
            for key,value in previous.items():
                if value is None: os.environ.pop(key,None)
                else: os.environ[key] = value
    return passed
