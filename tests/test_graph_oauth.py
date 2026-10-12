import pytest

from backend.graph_oauth import GraphOAuthToken, GRAPH_SCOPES
from backend.read_clients import ReadError


class FakeApplication:
    def __init__(self,accounts,result):
        self.accounts,self.result=accounts,result
        self.calls=0

    def get_accounts(self):
        return self.accounts

    def acquire_token_silent(self,scopes,account):
        self.calls+=1
        assert scopes==GRAPH_SCOPES
        assert account==self.accounts[0]
        return self.result


def test_worker_never_starts_interactive_login(tmp_path):
    token=GraphOAuthToken('client',tmp_path/'missing.bin')
    with pytest.raises(ReadError,match='graph_oauth_login_required'):
        token()


@pytest.mark.parametrize('accounts,result,reason',[
    ([],None,'graph_oauth_account_required'),
    ([{'id':'one'},{'id':'two'}],None,'graph_oauth_account_required'),
    ([{'id':'one'}],None,'graph_oauth_login_required'),
    ([{'id':'one'}],{'error':'interaction_required'},'graph_oauth_login_required'),
])
def test_worker_fails_closed_without_one_refreshable_account(tmp_path,monkeypatch,accounts,result,reason):
    token=GraphOAuthToken('client',tmp_path/'cache.bin')
    app=FakeApplication(accounts,result)
    monkeypatch.setattr(token,'application',lambda:app)
    with pytest.raises(ReadError,match=reason):token()
    assert app.calls==(1 if len(accounts)==1 else 0)


def test_worker_uses_silent_refresh_only(tmp_path,monkeypatch):
    token=GraphOAuthToken('client',tmp_path/'cache.bin')
    app=FakeApplication([{'id':'one'}],{'access_token':'opaque-token'})
    monkeypatch.setattr(token,'application',lambda:app)
    assert token()=='opaque-token'
    assert app.calls==1
