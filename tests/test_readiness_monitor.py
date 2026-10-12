import json
import httpx
import pytest
from scripts.readiness_monitor import check,local_url


def test_failed_delivery_survives_restart_and_recovery_order(tmp_path):
    healthy=False
    receive=False
    attempts=[]
    def handle(request):
        if request.method=='GET':return httpx.Response(200 if healthy else 503)
        attempts.append((request.headers['Idempotency-Key'],json.loads(request.content)))
        return httpx.Response(204 if receive else 503)
    client=httpx.Client(transport=httpx.MockTransport(handle))
    args=(tmp_path/'state.sqlite','http://127.0.0.1:8044/health/ready','http://127.0.0.1:8056/events')
    assert check(*args,client)['pending']==1
    assert check(*args,client)['pending']==1
    assert attempts[0][0]==attempts[1][0]
    healthy=True
    receive=True
    assert check(*args,client)=={'readiness':'healthy','delivered_this_check':2,'pending':0}
    assert [a[1]['type'] for a in attempts[-2:]]==['readiness.unavailable','readiness.healthy']
    assert check(*args,client)['delivered_this_check']==0


@pytest.mark.parametrize('url',['https://example.com/hook','http://127.0.0.1.evil.test/',
                              'http://secret@localhost/','http://localhost/?token=secret'])
def test_only_explicit_local_delivery(url):
    with pytest.raises(ValueError):local_url(url)
