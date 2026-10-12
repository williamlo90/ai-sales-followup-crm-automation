import json
from uuid import uuid4

import pytest

from scripts.graph_auth_configure import configure


def test_configure_preserves_project_mappings_and_keeps_sending_off(tmp_path):
    local=tmp_path/'local'
    local.mkdir()
    original={'local_tenant':str(uuid4()),'worker_id':str(uuid4()),
              'crm_write_enabled':True,'email_send_enabled':True,
              'email_recipient_allowlist':['buyer@example.test'],
              'graph':{'mailbox':'outlook@example.test','token_file':'local/secrets/graph-token',
                       'message_deals':{'message-1':'deal-1'}},
              'odoo':{'base_url':'http://127.0.0.1:8002','connector_tenant':str(uuid4()),
                      'company_id':1,'token_file':'local/secrets/odoo-token',
                      'deals':{'deal-1':{'opportunity_id':1,'assignee_id':2}}}}
    path=local/'connectors.json'
    path.write_text(json.dumps(original),encoding='utf-8')
    client_id=str(uuid4())
    assert configure(client_id,root=tmp_path)['email_send_enabled'] is False
    result=json.loads(path.read_text(encoding='utf-8'))
    assert result['graph']['oauth']['client_id']==client_id
    assert 'token_file' not in result['graph']
    assert result['graph']['message_deals']==original['graph']['message_deals']
    assert result['odoo']==original['odoo']
    assert result['email_send_enabled'] is False


def test_invalid_client_id_leaves_config_unchanged(tmp_path):
    local=tmp_path/'local'
    local.mkdir()
    path=local/'connectors.json'
    path.write_text('{}',encoding='utf-8')
    with pytest.raises(ValueError):configure('invalid',root=tmp_path)
    assert path.read_text(encoding='utf-8')=='{}'
