import json
from uuid import uuid4

import pytest

from scripts import graph_oauth_send_acceptance as probe


def setup_session(tmp_path, *, reserved=False):
    folder = tmp_path / 'local' / 'oauth-send'
    folder.mkdir(parents=True)
    (tmp_path / 'local' / 'graph-ingestion').mkdir()
    recipient = 'self@example.test'
    (folder / 'send-authorization.json').write_text(json.dumps(
        {'recipient': recipient, 'maximum_sends': 1, 'sent': False}))
    (tmp_path / 'local' / 'graph-ingestion' / 'send-authorization.json').write_text(json.dumps(
        {'recipient': recipient, 'maximum_sends': 1, 'sent': True}))
    (tmp_path / 'local' / 'connectors.json').write_text(json.dumps({
        'local_tenant': str(uuid4()), 'worker_id': str(uuid4()),
        'graph': {'mailbox': 'account@example.test', 'message_deals': {},
                  'oauth': {'client_id': str(uuid4()), 'cache_file': 'local/secrets/cache.bin'}}}))
    if reserved:
        (folder / 'send-attempt.json').write_text('{}')
    return folder


def test_one_approved_api_send_and_replay_without_second_dispatch(tmp_path, monkeypatch):
    folder = setup_session(tmp_path)
    monkeypatch.setattr(probe, 'ROOT', tmp_path)
    monkeypatch.setattr(probe, 'graph_token_reader', lambda cfg: lambda: 'fake-token')
    calls = []

    def dispatch(adapter, operation, payload):
        adapter.validate(operation, payload)
        calls.append(operation['id'])
        return adapter.receipt(operation, 'graph-request:' + str(uuid4()), 'accepted')

    monkeypatch.setattr(probe.GraphMailAdapter, 'dispatch', dispatch)
    monkeypatch.setattr(probe.GraphMailAdapter, 'observe',
                        lambda adapter, operation: adapter.receipt(operation, 'sent-id', 'sent'))
    result = probe.run('local/oauth-send')
    assert result['status'] == 'accepted'
    assert result['unapproved_send_denied'] and result['separate_approval']
    assert result['repeat_core_same_operation'] and result['sent_items_verified']
    assert len(calls) == 1
    assert (folder / 'send-operation.json').exists()
    assert json.loads((folder / 'send-authorization.json').read_text())['sent']


def test_reserved_session_stops_before_token_or_network(tmp_path, monkeypatch):
    setup_session(tmp_path, reserved=True)
    monkeypatch.setattr(probe, 'ROOT', tmp_path)
    monkeypatch.setattr(probe, 'graph_token_reader', lambda cfg: pytest.fail('Token must not be read'))
    with pytest.raises(ValueError, match='already attempted'):
        probe.run('local/oauth-send')
