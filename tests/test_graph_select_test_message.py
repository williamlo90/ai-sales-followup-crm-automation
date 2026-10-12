import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from scripts import graph_select_test_message as selector


class Reader:
    def __init__(self, items):
        self.items = items
        self.calls = 0

    def get(self, url, headers):
        self.calls += 1
        assert '/mailFolders/inbox/messages?' in url
        assert headers['Prefer'] == 'IdType="ImmutableId"'
        return {'value': self.items}


def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(selector, 'ROOT', tmp_path)
    local = tmp_path / 'local'
    local.mkdir()
    (local / 'connectors.json').write_text(json.dumps({
        'local_tenant': str(uuid4()), 'worker_id': str(uuid4()),
        'graph': {'mailbox': 'self@example.com', 'folder': 'inbox', 'message_deals': {},
                  'oauth': {'client_id': str(uuid4()), 'cache_file': 'local/secrets/cache.bin'}}
    }))
    return 'local/session'


def message(ident, subject, now, sender='person@gmail.com'):
    return {'id': ident, 'subject': subject, 'receivedDateTime': now.isoformat(),
            'from': {'emailAddress': {'address': sender}}}


def test_selects_only_one_recent_named_gmail_message(tmp_path, monkeypatch):
    session = setup(tmp_path, monkeypatch)
    now = datetime.now(timezone.utc)
    subject = 'Sales OAuth end-to-end 12 Okt'
    reader = Reader([message('other', 'Unrelated', now), message('selected', subject, now),
                     message('wrong-sender', subject, now, 'customer@example.com')])
    result = selector.select(subject, session, reader=reader, now=now)
    assert result['status'] == 'selected' and reader.calls == 1
    assert json.loads((tmp_path / session / 'selected-message.json').read_text())['id'] == 'selected'


def test_ambiguous_or_old_match_never_selects(tmp_path, monkeypatch):
    session = setup(tmp_path, monkeypatch)
    now = datetime.now(timezone.utc)
    subject = 'Sales OAuth end-to-end 12 Okt'
    duplicate = Reader([message('one', subject, now), message('two', subject, now)])
    assert selector.select(subject, session, reader=duplicate, now=now)['status'] == 'ambiguous'
    old = Reader([message('old', subject, now - timedelta(days=2))])
    assert selector.select(subject, session, reader=old, now=now)['status'] == 'not_found'
    assert not (tmp_path / session / 'selected-message.json').exists()
