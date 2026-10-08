import json
import httpx
import pytest
from backend.ingestion import GraphIngestion
from backend.read_clients import GraphReadClient
from backend.domain import DomainError
from backend.models import ProposalInput, ApprovalInput
from backend.models import SourceInput


def message(ident='m1',version='v1',modified='2026-10-08T10:00:00Z',text='Send pricing on 15 October.'):
    return {'id':ident,'changeKey':version,'lastModifiedDateTime':modified,'receivedDateTime':'2026-10-08T09:00:00Z',
            'body':{'contentType':'text','content':text}}


def setup(lab,mapping=None):
    client=GraphReadClient('lab','test@example.invalid',lambda:'fake',transport=httpx.MockTransport(lambda r:
        httpx.Response(200,json={'value':[message()],'@odata.deltaLink':'https://graph.microsoft.com'+client.path+'?$deltatoken=1'})))
    ingestor=GraphIngestion(lab[0],lab[1]['worker'],client,mapping or {'m1':'deal-1'})
    def page(items):return {'items':items,'complete':True,'checkpoint':{'tenant_id':'lab','mailbox_id':'test@example.invalid',
        'url':'https://graph.microsoft.com'+client.path+'?$deltatoken=1'}}
    return ingestor,page


def sources(lab):
    return lab[0].context(lab[1]['operator'],'deal-1')['sources']


def test_poll_restart_and_replay_no_revision_inflation(lab):
    ingest,page=setup(lab)
    assert ingest.poll()['changed']==1
    assert len(sources(lab))==2
    restarted,_=setup(lab)
    assert restarted.poll()['changed']==0
    assert restarted.state()[0]==2
    assert all(s['revision']==1 for s in sources(lab))
    with pytest.raises(DomainError,match='checkpoint_changed'):ingest.commit(0,page([message()]))


def test_unmapped_second_message_rolls_back_whole_page(lab):
    ingest,page=setup(lab)
    with pytest.raises(DomainError,match='message_mapping_required'):ingest.commit(0,page([message(),message('unmapped')]))
    assert len(sources(lab))==1 and ingest.state()==(0,None)
    with lab[0].store.connect() as conn:assert conn.execute('SELECT count(*) FROM ingestion_messages').fetchone()[0]==0


def test_db_failure_before_checkpoint_rolls_back_source(lab,monkeypatch):
    ingest,page=setup(lab)
    original=lab[0].audit
    def fail(conn,actor,action,resource):
        if action=='ingestion.page_committed':raise RuntimeError('simulated crash')
        return original(conn,actor,action,resource)
    monkeypatch.setattr(lab[0],'audit',fail)
    with pytest.raises(RuntimeError):ingest.commit(0,page([message()]))
    assert len(sources(lab))==1 and ingest.state()==(0,None)


def test_new_revision_invalidates_proposal_then_old_update_ignored(lab):
    ingest,page=setup(lab);ingest.poll()
    source=next(s for s in sources(lab) if s['external_id'].startswith('graph:'))
    sales,actors,_=lab
    proposal=sales.prepare(actors['operator'],ProposalInput(deal_id='deal-1',deal_version=1,
        evidence=[{'source_id':source['external_id'],'revision':1,'quote':source['text']}],summary='Pricing',
        due_at='2026-10-15T10:00:00Z',draft='Please confirm pricing.'))
    sales.approve(actors['approver'],proposal['id'],ApprovalInput(kind='crm',payload_hash=proposal['payload_hash']))
    assert ingest.commit(1,page([message(version='v2',modified='2026-10-08T11:00:00Z',text='Cancel pricing.')]))['changed']==1
    assert sales.get(actors['operator'],proposal['id'])['approval_valid'] is False
    assert ingest.commit(2,page([message()]))['changed']==0


def test_tombstone_invalidates_and_blocks_silent_resurrection(lab,proposal):
    ingest,page=setup(lab);ingest.poll()
    prepared=lab[0].prepare(lab[1]['operator'],ProposalInput(**proposal))
    assert ingest.commit(1,page([{'id':'m1','@removed':{'reason':'deleted'}}]))['changed']==1
    assert lab[0].get(lab[1]['operator'],prepared['id'])['validation_error']=='source_changed'
    assert ingest.commit(2,page([{'id':'m1','@removed':{}}]))['changed']==0
    with pytest.raises(DomainError,match='source_restore_requires_review'):ingest.commit(3,page([message()]))
    assert ingest.state()[0]==3
    assert any(s['deleted'] for s in sources(lab))


@pytest.mark.parametrize('change,error',[
    ({'changeKey':'v2'},'message_order_requires_review'),
    ({'body':{'contentType':'text','content':'Contradictory body'}},'message_version_conflict'),
    ({'body':{'contentType':'html','content':'<b>text</b>'}},'message_text_required'),
])
def test_ambiguous_versions_and_html_fail_without_checkpoint(lab,change,error):
    ingest,page=setup(lab);ingest.poll()
    with pytest.raises(DomainError,match=error):ingest.commit(1,page([message()|change]))
    assert ingest.state()[0]==1


def test_mapping_change_and_scope_denied(lab):
    ingest,page=setup(lab);ingest.poll()
    with pytest.raises(DomainError,match='ingestion_scope_mismatch'):
        GraphIngestion(lab[0],lab[1]['operator'],ingest.client,{'m1':'deal-1'})
    foreign=lab[1]['worker'].model_copy(update={'tenant_id':'other'})
    with pytest.raises(DomainError,match='ingestion_scope_mismatch'):GraphIngestion(lab[0],foreign,ingest.client,{})
    bad=page([]);bad['checkpoint']['tenant_id']='other'
    with pytest.raises(DomainError,match='ingestion_scope_mismatch'):ingest.commit(1,bad)


def test_bounded_pagination_preserves_continuation(lab,monkeypatch):
    ingest,page=setup(lab);calls=[]
    def next_page(checkpoint):
        calls.append(checkpoint)
        result=page([]);result['complete']=False
        result['checkpoint']['url']+='&page='+str(len(calls))
        return result
    monkeypatch.setattr(ingest.client,'page',next_page)
    assert ingest.poll_bounded(2)=={'generation':2,'changed':0,'complete':False,'pages':2}
    assert len(calls)==2 and ingest.state()[0]==2


def test_cross_folder_message_cannot_create_duplicate_source(lab):
    ingest,page=setup(lab);ingest.poll()
    other=GraphReadClient('lab','test@example.invalid',lambda:'fake',folder='archive')
    second=GraphIngestion(lab[0],lab[1]['worker'],other,{'m1':'deal-1'})
    payload=page([message()]);payload['checkpoint']['url']='https://graph.microsoft.com'+other.path+'?$deltatoken=2'
    with pytest.raises(DomainError,match='source_identity_collision'):second.commit(0,payload)
    assert second.state()==(0,None)


def test_deleted_evidence_cannot_prepare_even_with_current_revision(lab):
    ingest,page=setup(lab);ingest.poll()
    ingest.commit(1,page([{'id':'m1','@removed':{}}]))
    source=next(s for s in sources(lab) if s.get('deleted'))
    with pytest.raises(DomainError,match='source_deleted'):
        lab[0].prepare(lab[1]['operator'],ProposalInput(deal_id='deal-1',deal_version=1,
            evidence=[{'source_id':source['external_id'],'revision':source['revision'],'quote':source['text']}],
            summary='Invalid removed source',due_at='2026-10-15T10:00:00Z',draft='Invalid draft'))


def test_pre_tombstone_payload_replay_is_backward_compatible(lab):
    source=sources(lab)[0];source.pop('deleted')
    with lab[0].store.connect() as conn:
        conn.execute('UPDATE sources SET payload=? WHERE tenant=? AND id=?',(json.dumps(source),'lab',source['external_id']))
    assert lab[0].put_source(lab[1]['worker'],'deal-1',SourceInput(**source))['revision']==1
