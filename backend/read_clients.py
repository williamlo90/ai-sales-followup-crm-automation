"""Read-only business clients. Credentials are injected; no automatic discovery."""
import json
import time
from urllib.parse import quote, unquote, urlsplit
import httpx


class ReadError(Exception):
    def __init__(self,code,retry_after=None):
        super().__init__(code)
        self.code,self.retry_after=code,retry_after


class BoundedReader:
    def __init__(self,token,*,transport=None,sleep=time.sleep):
        self._token,self.transport,self.sleep=token,transport,sleep

    def get(self,url,headers=None):
        # Token callback may refresh outside this client. A rejected token is
        # surfaced once, never retried indefinitely or written to a log.
        try:token=self._token()
        except Exception:raise ReadError('credentials_unavailable') from None
        if not isinstance(token,str) or not token or any(c.isspace() for c in token):
            raise ReadError('credentials_missing')
        with httpx.Client(transport=self.transport,follow_redirects=False,trust_env=False,
                          timeout=httpx.Timeout(20,connect=5)) as client:
            for attempt in range(3):
                try:
                    with client.stream('GET',url,headers={'Authorization':'Bearer '+token,**(headers or {})}) as response:
                        if response.status_code in {401,403}:raise ReadError('credentials_rejected')
                        if response.status_code==410:raise ReadError('checkpoint_expired')
                        if response.status_code in {429,503,504}:
                            raw=response.headers.get('Retry-After','1')
                            wait=int(raw) if raw.isdecimal() and len(raw)<9 else None
                            if wait is None or wait>10 or attempt==2:raise ReadError('retry_later',wait)
                            self.sleep(wait);continue
                        if response.status_code not in {200,400,404}:raise ReadError('read_rejected')
                        content=bytearray()
                        for chunk in response.iter_bytes():
                            content.extend(chunk)
                            if len(content)>1_048_576:raise ReadError('response_limit')
                        data=json.loads(content)
                        if not isinstance(data,dict):raise ReadError('invalid_response')
                        if response.status_code!=200:
                            error=data.get('error')
                            if isinstance(error,dict) and error.get('code') in {'syncStateNotFound','SyncStateNotFound','InvalidDeltaToken'}:
                                raise ReadError('checkpoint_expired')
                            raise ReadError('read_rejected')
                        return data
                except httpx.HTTPError:
                    raise ReadError('read_transport_failure') from None
                except (ValueError,TypeError):
                    raise ReadError('invalid_response') from None
        raise ReadError('retry_later')


class GraphReadClient:
    def __init__(self,tenant_id,mailbox_id,token,*,folder='inbox',transport=None,sleep=time.sleep):
        if not tenant_id or not mailbox_id or not folder:raise ReadError('scope_missing')
        self.tenant_id,self.mailbox_id=tenant_id,mailbox_id
        self.path='/v1.0/users/'+quote(mailbox_id,safe='')+'/mailFolders/'+quote(folder,safe='')+'/messages/delta'
        self.checkpoint_paths={unquote(self.path),
            '/v1.0/users/'+mailbox_id+"/mailFolders('"+folder.replace("'","''")+"')/messages/delta"}
        self.initial='https://graph.microsoft.com'+self.path+'?$select=id,subject,body,from,receivedDateTime,lastModifiedDateTime,conversationId,changeKey'
        self.reader=BoundedReader(token,transport=transport,sleep=sleep)

    def message(self, ident):
        """Read one explicitly mapped message without scanning unrelated mailbox items."""
        if not isinstance(ident,str) or not ident or len(ident)>4096 or any(c.isspace() for c in ident):
            raise ReadError('invalid_message_id')
        url='https://graph.microsoft.com/v1.0/users/'+quote(self.mailbox_id,safe='')+'/messages/'+quote(ident,safe='')
        url+='?$select=id,subject,body,from,receivedDateTime,lastModifiedDateTime,conversationId,changeKey'
        item=self.reader.get(url,{'Prefer':'outlook.body-content-type="text", IdType="ImmutableId"'})
        if item.get('id')!=ident:raise ReadError('message_identity_mismatch')
        return item

    def validate_link(self,link):
        if not isinstance(link,str) or len(link)>16000:raise ReadError('invalid_checkpoint')
        try:
            parsed=urlsplit(link)
            valid=(parsed.scheme=='https' and parsed.netloc=='graph.microsoft.com' and unquote(parsed.path) in self.checkpoint_paths
                   and not parsed.fragment and not parsed.username and not parsed.password)
        except ValueError:valid=False
        if not valid:raise ReadError('checkpoint_scope_mismatch')
        return link

    def page(self,checkpoint=None):
        if checkpoint is None:url=self.initial
        else:
            if (not isinstance(checkpoint,dict) or checkpoint.get('tenant_id')!=self.tenant_id
                    or checkpoint.get('mailbox_id')!=self.mailbox_id):raise ReadError('checkpoint_scope_mismatch')
            url=self.validate_link(checkpoint.get('url'))
        data=self.reader.get(url,{'Prefer':'outlook.body-content-type="text", IdType="ImmutableId"'})
        items=data.get('value')
        if not isinstance(items,list) or len(items)>1000 or any(not isinstance(i,dict) or not isinstance(i.get('id'),str) for i in items):
            raise ReadError('invalid_message_page')
        next_link,delta=data.get('@odata.nextLink'),data.get('@odata.deltaLink')
        if bool(next_link)==bool(delta):raise ReadError('invalid_checkpoint')
        link=self.validate_link(next_link or delta)
        if next_link==url:raise ReadError('pagination_cycle')
        # Caller must commit this checkpoint only in the same transaction as
        # idempotent ingestion of this page, including @removed tombstones.
        return {'items':items,'complete':bool(delta),'checkpoint':{
            'tenant_id':self.tenant_id,'mailbox_id':self.mailbox_id,'url':link}}


class OdooReadClient:
    def __init__(self,base,tenant_id,company_id,token,*,transport=None,sleep=time.sleep):
        try:
            parsed=urlsplit(base)
            valid=(parsed.scheme=='http' and parsed.hostname in {'127.0.0.1','localhost'} and
                   parsed.path in {'','/'} and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment)
        except ValueError:valid=False
        if not valid or not tenant_id or type(company_id) is not int or company_id<1:raise ReadError('invalid_odoo_scope')
        self.base,self.tenant_id,self.company_id=base.rstrip('/'),tenant_id,company_id
        self.reader=BoundedReader(token,transport=transport,sleep=sleep)

    def identity(self):
        me=self.reader.get(self.base+'/me')
        if me.get('tenant_id')!=self.tenant_id or me.get('role') not in {'operator','approver','auditor'}:
            raise ReadError('connector_scope_mismatch')

    def check_record(self,record):
        if (not isinstance(record,dict) or record.get('company_id')!=self.company_id or record.get('source')!='odoo:crm.lead'
                or type(record.get('id')) is not int or record['id']<1 or not isinstance(record.get('version'),str)):
            raise ReadError('connector_record_mismatch')
        return record

    def opportunities(self):
        self.identity()
        data=self.reader.get(self.base+'/v1/opportunities')
        # Connector #2 caps at 100 and has no opportunity pagination contract.
        # Fail rather than silently pretend an unsupported cursor was consumed.
        if set(data)!={'items'} or not isinstance(data['items'],list) or len(data['items'])>100:
            raise ReadError('connector_list_contract_mismatch')
        records=[self.check_record(item) for item in data['items']]
        if len({r['id'] for r in records})!=len(records):raise ReadError('connector_duplicate_record')
        return records

    def opportunity(self,ident):
        if type(ident) is not int or ident<1:raise ReadError('invalid_opportunity_id')
        self.identity()
        record=self.check_record(self.reader.get(self.base+f'/v1/opportunities/{ident}'))
        if record['id']!=ident:raise ReadError('connector_record_mismatch')
        return record
