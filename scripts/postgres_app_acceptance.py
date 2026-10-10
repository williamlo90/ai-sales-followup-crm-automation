"""FastAPI/shared-core acceptance against real PostgreSQL; no external effects."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from uuid import uuid4
from fastapi.testclient import TestClient
from backend.app import from_environment


def check_application(owner, dsn, tenants):
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
                source['revision'] = 2; source['text'] = 'Morgan cancelled the checklist.'
                assert client.put('/v1/ingest/deals/app-deal/sources',headers=headers('worker'),json=source).status_code == 200
                stale = client.get(f"/v1/proposals/{p['id']}",headers=headers('auditor')).json()
                assert stale['validation_error'] == 'source_changed' and stale['approval_valid'] is False
                assert client.post(f"/v1/proposals/{p['id']}/approvals",headers=headers('approver'),json={'kind':'email','payload_hash':p['payload_hash']}).status_code == 409
                passed.append('app_source_revision_invalidates_approval')
                assert owner.execute('SELECT count(*) FROM operations').fetchone()[0] == 0
                passed.append('app_no_external_operations')
        finally:
            for key,value in previous.items():
                if value is None: os.environ.pop(key,None)
                else: os.environ[key] = value
    return passed
