"""Atomic Graph page ingestion using explicit message-to-deal mapping."""
import hashlib
import json
from datetime import datetime
from backend.domain import DomainError, canonical
from backend.models import SourceInput


def aware(value):
    try:
        parsed=datetime.fromisoformat(value)
        if parsed.tzinfo is None:raise ValueError()
        return parsed
    except (ValueError,TypeError):raise DomainError('invalid_message_timestamp',422) from None


class GraphIngestion:
    def __init__(self,sales,actor,client,mapping):
        if actor.role!='worker' or actor.tenant_id!=client.tenant_id:
            raise DomainError('ingestion_scope_mismatch',403)
        self.sales,self.actor,self.client,self.mapping=sales,actor,client,dict(mapping)
        self.stream=hashlib.sha256(client.path.encode()).hexdigest()

    def state(self):
        with self.sales.store.connect(self.actor) as conn:
            row=conn.execute('SELECT * FROM ingestion_streams WHERE tenant=? AND stream=?',(self.actor.tenant_id,self.stream)).fetchone()
            return (row['generation'],json.loads(row['checkpoint'])) if row else (0,None)

    def poll(self):
        generation,checkpoint=self.state()
        page=self.client.page(checkpoint) # No DB transaction spans network I/O.
        return self.commit(generation,page)

    def selected(self, external_id):
        if external_id not in self.mapping:raise DomainError('message_mapping_required')
        item=self.client.message(external_id)
        with self.sales.store.connect(self.actor) as conn:
            changed=self.ingest(conn,item)
            self.sales.audit(conn,self.actor,'ingestion.selected',external_id)
        return {'changed':changed,'external_id':external_id,'checkpoint_advanced':False}

    def poll_bounded(self,max_pages=10):
        if type(max_pages) is not int or not 1<=max_pages<=10:raise DomainError('invalid_page_budget',422)
        seen=set();changed=0
        for count in range(max_pages):
            _,checkpoint=self.state()
            marker=canonical(checkpoint)
            if marker in seen:raise DomainError('pagination_cycle')
            seen.add(marker)
            result=self.poll();changed+=result['changed']
            if result['complete']:break
        return {**result,'changed':changed,'pages':count+1}

    def commit(self,generation,page):
        checkpoint=page['checkpoint']
        if checkpoint.get('tenant_id')!=self.actor.tenant_id or checkpoint.get('mailbox_id')!=self.client.mailbox_id:
            raise DomainError('ingestion_scope_mismatch',403)
        self.client.validate_link(checkpoint.get('url'))
        if not isinstance(page.get('items'),list) or len(page['items'])>1000:raise DomainError('invalid_ingestion_page',422)
        changed=0
        with self.sales.store.connect(self.actor) as conn:
            row=conn.execute('SELECT generation FROM ingestion_streams WHERE tenant=? AND stream=?',(self.actor.tenant_id,self.stream)).fetchone()
            if (row['generation'] if row else 0)!=generation:raise DomainError('checkpoint_changed')
            for item in page['items']:
                changed+=self.ingest(conn,item)
            conn.execute('INSERT INTO ingestion_streams VALUES(?,?,?,?) ON CONFLICT(tenant,stream) DO UPDATE SET generation=excluded.generation,checkpoint=excluded.checkpoint',
                (self.actor.tenant_id,self.stream,generation+1,canonical(checkpoint)))
            self.sales.audit(conn,self.actor,'ingestion.page_committed',self.stream)
        return {'generation':generation+1,'changed':changed,'complete':page['complete']}

    def ingest(self,conn,item):
        if not isinstance(item,dict) or not isinstance(item.get('id'),str) or not item['id']:
            raise DomainError('invalid_message',422)
        external=item['id'];deal=self.mapping.get(external)
        if not deal:raise DomainError('message_mapping_required')
        self.sales.scope(self.actor,deal,{'worker'})
        old=conn.execute('SELECT * FROM ingestion_messages WHERE tenant=? AND stream=? AND external_id=?',
                         (self.actor.tenant_id,self.stream,external)).fetchone()
        if old and old['deal_id']!=deal:raise DomainError('source_link_conflict')
        removed='@removed' in item
        if old and old['deleted']:
            if removed:return 0
            # A delayed update must not resurrect removed evidence silently.
            raise DomainError('source_restore_requires_review')
        source_id='graph:'+hashlib.sha256(canonical([self.client.mailbox_id,external]).encode()).hexdigest()
        source=conn.execute('SELECT * FROM sources WHERE tenant=? AND id=?',(self.actor.tenant_id,source_id)).fetchone()
        if source and not old:raise DomainError('source_identity_collision')
        if removed:
            timestamp=json.loads(source['payload'])['occurred_at'] if source else self.sales.clock().isoformat()
            body='[Source removed from monitored folder]';change_key=None;modified=None
        else:
            body_data=item.get('body')
            if not isinstance(body_data,dict) or body_data.get('contentType','').lower()!='text':raise DomainError('message_text_required',422)
            body=body_data.get('content')
            if not isinstance(body,str) or not body:raise DomainError('message_text_required',422)
            timestamp=item.get('receivedDateTime');aware(timestamp)
            modified=item.get('lastModifiedDateTime');modified_time=aware(modified)
            change_key=item.get('changeKey')
            if not isinstance(change_key,str) or not change_key:raise DomainError('message_version_required',422)
            digest=hashlib.sha256(canonical([body,timestamp]).encode()).hexdigest()
            if old:
                previous=aware(old['modified_at'])
                if modified_time<previous:return 0
                if change_key==old['change_key']:
                    if digest!=old['content_hash']:raise DomainError('message_version_conflict')
                    return 0
                if modified_time==previous:raise DomainError('message_order_requires_review')
        digest=hashlib.sha256(canonical([body,timestamp]).encode()).hexdigest()
        data=SourceInput(external_id=source_id,revision=source['revision']+1 if source else 1,
                         occurred_at=timestamp,text=body,deleted=removed)
        self.sales.put_source_in_transaction(conn,self.actor,deal,data)
        conn.execute('INSERT INTO ingestion_messages VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(tenant,stream,external_id) DO UPDATE SET change_key=excluded.change_key,modified_at=excluded.modified_at,deleted=excluded.deleted,content_hash=excluded.content_hash',
            (self.actor.tenant_id,self.stream,external,source_id,deal,change_key,modified,int(removed),digest))
        return 1
