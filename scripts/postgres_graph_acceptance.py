"""Real Graph delta and real PostgreSQL, scoped to the selected synthetic mail."""
import json
from uuid import uuid4
from backend.config import ROOT
from backend.connector_runtime import token_reader
from backend.domain import SalesService
from backend.models import Actor, DealInput
from backend.postgres_store import PostgresStore
from backend.read_clients import GraphReadClient
from backend.ingestion import GraphIngestion


def check_graph(owner, dsn, tenant):
    cfg = json.loads((ROOT/'local/connectors.json').read_text(encoding='utf-8-sig'))
    selected = json.loads((ROOT/'local/graph-ingestion/selected-message.json').read_text())
    assert selected['mailbox'] == cfg['graph']['mailbox']
    assert selected['subject'] in (
        '[SALES-P04-TEST-20261010-A] Jadwal demo Northstar',
        'Subject: [SALES-P04-TEST-20261010-A] Jadwal demo Northstar')
    worker = Actor(id=str(uuid4()), tenant_id=str(tenant), role='worker', deal_ids={'graph-test'})
    owner.execute('INSERT INTO actors(tenant_id,id,role) VALUES(%s,%s,%s)',
                  (tenant, worker.id, worker.role))
    sales = SalesService(PostgresStore(dsn))
    sales.put_deal(worker, 'graph-test', DealInput(account_id='northstar-lab',
        title='Synthetic Graph acceptance', recipient='buyer@example.test', version=1))
    client = GraphReadClient(str(tenant), selected['mailbox'], token_reader(cfg['graph']['token_file']))
    # Preflight only IDs: refuse an inbox containing unrelated messages.
    base = client.initial.split('/messages/delta')[0]
    listing = client.reader.get(base+'/messages?$select=id&$top=2', {'Prefer':'IdType="ImmutableId"'})
    assert [x['id'] for x in listing['value']] == [selected['id']]
    assert not listing.get('@odata.nextLink')
    ingestion = GraphIngestion(sales, worker, client, {selected['id']:'graph-test'})
    page = client.page()
    assert page['complete'] and len(page['items']) == 1
    assert page['items'][0]['id'] == selected['id']
    assert page['items'][0]['subject'] == selected['subject']
    first = ingestion.commit(0, page)
    assert first['changed'] == 1
    # Replay the real fetched page; do not manufacture a checkpoint or response.
    assert ingestion.commit(1, page)['changed'] == 0
    resumed = GraphIngestion(SalesService(PostgresStore(dsn)), worker, client,
                            {selected['id']:'graph-test'})
    assert resumed.state()[0] == 2
    subsequent = resumed.poll()
    assert subsequent['changed'] == 0 and subsequent['complete']
    with resumed.sales.store.connect(worker) as conn:
        assert conn.execute('SELECT count(*) FROM sources').fetchone()[0] == 1
        assert conn.execute('SELECT revision FROM sources').fetchone()[0] == 1
    return ['real_graph_delta_page_committed_to_postgres',
            'real_page_replay_no_duplicate_or_revision_inflation',
            'reopened_store_resumes_saved_checkpoint_with_real_graph',
            'one_source_revision_one_after_resumed_poll']
