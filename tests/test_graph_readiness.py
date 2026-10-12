import json
import httpx
import pytest
from backend.read_clients import ReadError
from scripts.graph_readiness import check


def setup_config(tmp_path, token='test-secret'):
    (tmp_path / 'local').mkdir()
    (tmp_path / 'local/token').write_text(token)
    return {'mailbox': 'test@outlook.com', 'folder': 'inbox',
            'token_file': 'local/token', 'message_deals': {}}


def test_bounded_read_does_not_expose_profile_or_message(tmp_path):
    cfg = setup_config(tmp_path)
    calls = []
    def respond(req):
        calls.append(req)
        assert req.method == 'GET'
        if req.url.path.endswith('/me'):
            return httpx.Response(200, json={'id': 'private-id', 'mail': 'test@outlook.com'})
        assert req.url.params['$top'] == '1'
        assert req.url.params['$select'] == 'id'
        return httpx.Response(200, json={'value': [{'id': 'private-message'}],
                                       '@odata.nextLink': 'https://evil.invalid'})
    result = check(cfg, root=tmp_path, transport=httpx.MockTransport(respond))
    assert result['status'] == 'passed' and len(calls) == 2
    assert 'private' not in json.dumps(result) and 'test-secret' not in json.dumps(result)


def test_wrong_account_stops_before_mailbox(tmp_path):
    cfg = setup_config(tmp_path)
    calls = []
    def respond(req):
        calls.append(req)
        return httpx.Response(200, json={'id': 'other', 'mail': 'other@outlook.com'})
    with pytest.raises(ReadError, match='mailbox_identity_mismatch'):
        check(cfg, root=tmp_path, transport=httpx.MockTransport(respond))
    assert len(calls) == 1


def test_empty_token_never_connects(tmp_path):
    cfg = setup_config(tmp_path, '')
    def respond(req):
        pytest.fail('No network allowed without token')
    with pytest.raises(ReadError, match='credentials_unavailable'):
        check(cfg, root=tmp_path, transport=httpx.MockTransport(respond))


def test_rejected_token_is_sanitized(tmp_path):
    cfg = setup_config(tmp_path)
    with pytest.raises(ReadError, match='credentials_rejected') as error:
        check(cfg, root=tmp_path, transport=httpx.MockTransport(
            lambda req: httpx.Response(401, text='test-secret')))
    assert 'test-secret' not in str(error.value)
