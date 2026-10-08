"""Send an immutable locally approved draft body; never resend on observation."""
import hashlib
from urllib.parse import quote, urlencode
from uuid import UUID
from datetime import datetime
import httpx
from backend.domain import canonical
from backend.read_clients import BoundedReader, ReadError

PROPERTY='String {19fe4799-bd9a-47fb-bc72-41e3c32706d1} Name SalesOperation'


class GraphMailAdapter:
    def __init__(self,local_tenant,mailbox,token,payloads,*,recipients=frozenset(),send_enabled=False,transport=None):
        if not local_tenant or not mailbox:raise ReadError('mailbox_scope_missing')
        self.tenant,self.mailbox,self.payloads=local_tenant,mailbox,payloads
        self.base='https://graph.microsoft.com/v1.0/users/'+quote(mailbox,safe='')
        self.reader=BoundedReader(token,transport=transport)
        self.recipients=frozenset(recipients)
        self.send_enabled=send_enabled

    def validate(self,operation,payload):
        if operation.get('tenant')!=self.tenant or operation.get('kind')!='email':raise ReadError('mailbox_scope_mismatch')
        try:UUID(operation['id'])
        except (ValueError,KeyError,TypeError):raise ReadError('invalid_operation') from None
        if not isinstance(payload,dict) or hashlib.sha256(canonical(payload).encode()).hexdigest()!=operation.get('payload_hash'):
            raise ReadError('mail_payload_changed')
        if not all(isinstance(payload.get(k),str) and payload[k] for k in ['recipient','summary','draft']):
            raise ReadError('invalid_mail_payload')

    def dispatch(self,operation,payload):
        if not self.send_enabled:raise ReadError('mail_send_disabled')
        self.validate(operation,payload)
        if payload['recipient'] not in self.recipients:raise ReadError('recipient_not_allowlisted')
        # Payload is sent atomically; no mutable mailbox draft between review and send.
        body={'message':{'subject':payload['summary'],'body':{'contentType':'Text','content':payload['draft']},
            'toRecipients':[{'emailAddress':{'address':payload['recipient']}}],
            'singleValueExtendedProperties':[{'id':PROPERTY,'value':operation['id']}],
            'internetMessageHeaders':[{'name':'x-sales-operation-id','value':operation['id']}]}}
        try:token=self.reader._token()
        except Exception:raise ReadError('credentials_unavailable') from None
        if not isinstance(token,str) or not token or any(c.isspace() for c in token):raise ReadError('credentials_missing')
        try:
            with httpx.Client(transport=self.reader.transport,trust_env=False,follow_redirects=False,timeout=20) as client:
                with client.stream('POST',self.base+'/sendMail',json=body,
                    headers={'Authorization':'Bearer '+token,'client-request-id':operation['id']}) as response:
                    if response.status_code!=202:raise ReadError('mail_send_outcome_unknown')
                    # This ID is a Graph request receipt, not a message/delivery ID.
                    try:receipt_id=str(UUID(response.headers.get('request-id','')))
                    except ValueError:raise ReadError('mail_acceptance_receipt_missing') from None
                    return self.receipt(operation,'graph-request:'+receipt_id,'accepted')
        except httpx.HTTPError:raise ReadError('mail_send_outcome_unknown') from None

    def receipt(self,operation,external_id,state):
        return {'operation_id':operation['id'],'tenant_id':self.tenant,'payload_hash':operation['payload_hash'],
                'external_id':external_id,'state':state}

    def observe(self,operation):
        if operation.get('tenant')!=self.tenant or operation.get('kind')!='email':raise ReadError('mailbox_scope_mismatch')
        payload=self.payloads(operation['tenant'],operation['proposal_id'])
        self.validate(operation,payload)
        params={'$filter':f"singleValueExtendedProperties/Any(ep: ep/id eq '{PROPERTY}' and ep/value eq '{operation['id']}')",
                '$expand':f"singleValueExtendedProperties($filter=id eq '{PROPERTY}')",
                '$select':'id,isDraft,subject,body,toRecipients,ccRecipients,bccRecipients,sentDateTime', '$top':'2'}
        data=self.reader.get(self.base+'/mailFolders/sentitems/messages?'+urlencode(params),
                             {'Prefer':'outlook.body-content-type="text", IdType="ImmutableId"'})
        items=data.get('value')
        if not isinstance(items,list):raise ReadError('mail_observation_invalid')
        if len(items)!=1 or data.get('@odata.nextLink'):return None
        message=items[0]
        if not isinstance(message,dict):raise ReadError('mail_observation_invalid')
        props=message.get('singleValueExtendedProperties',[])
        # Display names are irrelevant; address lists and content must match.
        recipients=message.get('toRecipients')
        if not isinstance(recipients,list) or any(not isinstance(r,dict) or not isinstance(r.get('emailAddress'),dict) for r in recipients):
            raise ReadError('mail_observation_invalid')
        addresses=[r['emailAddress'].get('address') for r in recipients]
        try:
            sent=datetime.fromisoformat(message.get('sentDateTime'))
            if sent.tzinfo is None:raise ValueError()
        except (TypeError,ValueError):raise ReadError('mail_observation_invalid') from None
        body=message.get('body')
        if (not isinstance(message.get('id'),str) or not message['id'] or message.get('isDraft') is not False
            or not message.get('sentDateTime') or message.get('subject')!=payload['summary']
            or addresses!=[payload['recipient']] or message.get('ccRecipients') or message.get('bccRecipients')
            or not isinstance(body,dict) or body.get('contentType','').lower()!='text' or body.get('content')!=payload['draft']
            or props!=[{'id':PROPERTY,'value':operation['id']}]):
            raise ReadError('mail_observation_mismatch')
        return self.receipt(operation,message['id'],'sent')


class EffectRouter:
    def __init__(self,crm,mail):self.adapters={'crm':crm,'email':mail}
    def dispatch(self,operation,payload):
        adapter=self.adapters.get(operation['kind'])
        if adapter is None:raise ReadError('effect_adapter_unavailable')
        return adapter.dispatch(operation,payload)
    def observe(self,operation):
        adapter=self.adapters.get(operation['kind'])
        if adapter is None:raise ReadError('effect_adapter_unavailable')
        return adapter.observe(operation)
