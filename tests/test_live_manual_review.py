from uuid import uuid4
from fastapi.testclient import TestClient
from scripts.live_manual_review import create_app


def test_live_core_authority_and_replay(tmp_path):
    app=create_app(tmp_path);client=TestClient(app,base_url='http://127.0.0.1:8046')
    data={'session_id':str(uuid4())};headers={'X-Worksheet-Key':app.state.test_key}
    assert client.post('/assist/manual-p1-2',json=data).status_code==403
    assert client.post('/assist/manual-p1-1',json=data,headers=headers).status_code==404
    result=client.post('/assist/manual-p1-2',json=data,headers=headers)
    assert result.status_code==200
    assert result.json()['answer']=={'eligible':True,'reason':'due_and_approved'}
    assert result.json()['core_seconds']>=0
    assert client.post('/assist/manual-p1-2',json=data,headers=headers).status_code==409
    assert client.post('/assist/manual-p2-1',json=data,headers={**headers,'Origin':'https://example.test'}).status_code==403
    assert client.get('/',headers={'Host':'other.test'}).status_code==403
    html=client.get('/').text
    assert '__PACK__' not in html and 'fetch(' in html
