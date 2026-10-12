import json
import pytest
from scripts import graph_send_acceptance as probe


@pytest.mark.parametrize('reserved,sent',[(True,False),(False,True)])
def test_send_budget_blocks_before_database_or_network(tmp_path,monkeypatch,reserved,sent):
    monkeypatch.setattr(probe,'ROOT',tmp_path)
    folder=tmp_path/'local/graph-ingestion';folder.mkdir(parents=True)
    (folder/'send-authorization.json').write_text(json.dumps({'maximum_sends':1,'sent':sent}))
    if reserved:(folder/'send-attempt.json').write_text('{}')
    monkeypatch.setattr(probe.psycopg,'connect',lambda *a,**k:pytest.fail('No DB/network allowed'))
    with pytest.raises(ValueError):probe.run('unused')


def test_missing_token_cannot_reserve_attempt(tmp_path,monkeypatch):
    monkeypatch.setattr(probe,'ROOT',tmp_path)
    folder=tmp_path/'local/graph-ingestion';folder.mkdir(parents=True)
    (folder/'send-authorization.json').write_text(json.dumps({'maximum_sends':1,'sent':False}))
    (tmp_path/'local/connectors.json').write_text(json.dumps({'graph':{'token_file':'local/missing'}}))
    def unavailable(*args):
        def read():raise ValueError('missing')
        return read
    monkeypatch.setattr(probe,'token_reader',unavailable)
    monkeypatch.setattr(probe.psycopg,'connect',lambda *a,**k:pytest.fail('No DB/network allowed'))
    with pytest.raises(ValueError):probe.run('unused')
    assert not (folder/'send-attempt.json').exists()

def test_send_session_cannot_escape_project(tmp_path,monkeypatch):
    monkeypatch.setattr(probe,'ROOT',tmp_path)
    monkeypatch.setenv('SALES_GRAPH_SEND_SESSION','../foreign')
    monkeypatch.setattr(probe.psycopg,'connect',lambda *a,**k:pytest.fail('No DB/network allowed'))
    with pytest.raises(ValueError,match='inside project'):probe.run('unused')
