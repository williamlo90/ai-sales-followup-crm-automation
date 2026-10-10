import json
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from backend.connector_runtime import compose
from backend.domain import SalesService
from backend.store import Store
from backend.models import Actor
from backend.app import create_app
from conftest import auth
import hashlib


def configuration(tmp_path):
    (tmp_path/'local').mkdir()
    worker = Actor(id=str(uuid4()),tenant_id=str(uuid4()),role='worker',deal_ids={'deal-1'})
    cfg = {'local_tenant':worker.tenant_id,'worker_id':worker.id,
        'graph':{'mailbox':'sandbox@example.test','token_file':'local/not-provided.secret','message_deals':{'message':'deal-1'}},
        'odoo':{'base_url':'http://127.0.0.1:8002','connector_tenant':str(uuid4()),'company_id':1,
                'token_file':'local/not-provided-odoo.secret','deals':{'deal-1':{'opportunity_id':1,'assignee_id':2}}}}
    return worker,cfg


def build(tmp_path,worker,cfg):
    (tmp_path/'local/connectors.json').write_text(json.dumps(cfg))
    return compose(SalesService(Store(tmp_path/'store.sqlite')),{'worker':worker},'local/connectors.json',root=tmp_path)


def test_composition_does_not_read_missing_tokens_or_enable_effects(tmp_path):
    worker,cfg = configuration(tmp_path);runtime = build(tmp_path,worker,cfg)
    assert runtime.execution.enabled is False and runtime.execution.send_enabled is False
    assert runtime.connector.write_enabled is False
    assert runtime.ingestion.actor == worker
    assert runtime.connector.local_tenant == worker.tenant_id


@pytest.mark.parametrize('change',['worker','tenant','scope','token_path','send_flag'])
def test_invalid_scope_or_attempted_send_enable_rejected(tmp_path,change):
    worker,cfg = configuration(tmp_path)
    if change=='worker':cfg['worker_id']=str(uuid4())
    if change=='tenant':cfg['local_tenant']=str(uuid4())
    if change=='scope':cfg['graph']['message_deals']['message']='out-of-scope'
    if change=='token_path':cfg['graph']['token_file']='../sibling/.env'
    if change=='send_flag':cfg['send_enabled']=True
    with pytest.raises(ValueError):build(tmp_path,worker,cfg)


def test_poll_endpoint_rejects_different_worker_before_network(tmp_path):
    worker,cfg = configuration(tmp_path);runtime = build(tmp_path,worker,cfg)
    other = worker.model_copy(update={'id':str(uuid4())})
    identities = {hashlib.sha256(b'worker').hexdigest():other}
    app = create_app(runtime.execution.sales,identities,ingestion=runtime.ingestion)
    with TestClient(app) as client:
        assert client.post('/v1/ingest/graph/poll',headers=auth('worker')).status_code==404
