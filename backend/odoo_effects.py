"""Odoo #2 activity effect boundary. No approver impersonation or retry endpoint."""
import hashlib
import json
from datetime import datetime, timezone
from uuid import UUID
from zoneinfo import ZoneInfo
import httpx
from backend.domain import canonical
from backend.read_clients import OdooReadClient, ReadError


class OdooActivityAdapter:
    def __init__(self,client: OdooReadClient,bindings,deal_mapping,*,timezone_name='UTC',write_enabled=False,clock=None):
        self.client,self.bindings,self.deal_mapping=client,bindings,dict(deal_mapping)
        self.zone=ZoneInfo(timezone_name)
        self.write_enabled=write_enabled
        self.clock=clock or (lambda:datetime.now(timezone.utc))

    def binding(self,operation):
        if operation['kind']!='crm':raise ReadError('unsupported_effect')
        binding=self.bindings(operation['tenant'],operation['proposal_id'])
        if (not isinstance(binding,dict) or binding.get('local_payload_hash')!=operation['payload_hash']
            or binding.get('connector_tenant')!=self.client.tenant_id):
            raise ReadError('connector_binding_missing_or_stale')
        for name in ['proposal_id','approval_id','actor_id']:
            try:UUID(binding[name])
            except (ValueError,KeyError,TypeError):raise ReadError('invalid_connector_binding') from None
        return binding

    def workspace(self,binding,*,check_expiry):
        me=self.client.reader.get(self.client.base+'/me')
        if me.get('tenant_id')!=self.client.tenant_id or me.get('id')!=binding['actor_id'] or me.get('role')!='operator':
            raise ReadError('connector_actor_mismatch')
        data=self.client.reader.get(self.client.base+'/v1/workspace/proposals/'+binding['proposal_id'])
        proposal,approval=data.get('proposal'),data.get('approval')
        if not isinstance(proposal,dict) or not isinstance(approval,dict):raise ReadError('connector_approval_required')
        preview=proposal.get('preview')
        if (proposal.get('id')!=binding['proposal_id'] or proposal.get('tenant_id')!=self.client.tenant_id
            or proposal.get('actor_id')!=binding['actor_id'] or proposal.get('kind')!='activity'
            or proposal.get('contract_version')!='1.0' or preview!=binding.get('preview')
            or not isinstance(preview,dict) or preview.get('company_id')!=self.client.company_id):
            raise ReadError('connector_proposal_mismatch')
        digest=hashlib.sha256(canonical(preview).encode()).hexdigest()
        if (proposal.get('payload_hash')!=digest or approval.get('payload_hash')!=digest
            or approval.get('id')!=binding['approval_id'] or approval.get('proposal_id')!=proposal['id']
            or approval.get('tenant_id')!=self.client.tenant_id or not approval.get('approver_id')
            or approval.get('approver_id')==binding['actor_id']):raise ReadError('connector_approval_mismatch')
        if check_expiry:
            for value in [proposal.get('expires_at'),approval.get('expires_at')]:
                try:expiry=datetime.fromisoformat(value)
                except (ValueError,TypeError):raise ReadError('connector_expiry_invalid') from None
                if expiry.tzinfo is None or expiry<=self.clock():raise ReadError('connector_approval_expired')
        return data

    def expected_activity(self,payload):
        mapping=self.deal_mapping.get(payload['deal_id'])
        if not mapping:raise ReadError('deal_mapping_required')
        expected={'kind':'activity','company_id':self.client.company_id,'opportunity_id':mapping['opportunity_id'],
                  'assignee_id':mapping['assignee_id'],'due_date':datetime.fromisoformat(payload['due_at']).astimezone(self.zone).date().isoformat(),
                  'summary':payload['summary'],'contract_version':'1.0'}
        return expected

    def preparation(self,payload):
        expected=self.expected_activity(payload)
        record=self.client.opportunity(expected['opportunity_id'])
        # The connector fingerprints lead, assignee, company and binding state.
        # A lead write_date is not that fingerprint and cannot prefill it.
        if len(payload['summary'])>120 or '<' in payload['summary'] or '>' in payload['summary']:
            raise ReadError('activity_preview_mismatch')
        return {'preview':expected,'opportunity_version':record['version'],
                'connector_preparation_required':True,'timezone':str(self.zone),
                'action':'create_activity','write_performed':False}

    def validate_activity(self,payload,binding):
        expected=self.expected_activity(payload)
        preview=binding['preview']
        if (len(payload['summary'])>120 or '<' in payload['summary'] or '>' in payload['summary']
            or set(preview)!=set(expected)|{'source_version'} or not isinstance(preview.get('source_version'),str)
            or not preview['source_version'] or any(preview.get(k)!=v for k,v in expected.items())):
            raise ReadError('activity_preview_mismatch')

    def dispatch(self,operation,payload):
        if not self.write_enabled:raise ReadError('connector_write_disabled')
        binding=self.binding(operation)
        self.validate_activity(payload,binding)
        workspace=self.workspace(binding,check_expiry=True)
        remote=workspace.get('operation')
        if remote is None:
            remote=self.post('/v1/proposals/'+binding['proposal_id']+'/execute',
                {'approval_id':binding['approval_id'],'idempotency_key':str(UUID(operation['id']))})
        return self.receipt(operation,binding,remote)

    def observe(self,operation):
        binding=self.binding(operation)
        workspace=self.workspace(binding,check_expiry=False)
        remote=workspace.get('operation')
        if remote is None:return None # Missing remote operation never triggers execute.
        self.validate_operation(operation,binding,remote)
        remote=self.client.reader.get(self.client.base+'/v1/operations/'+remote['id'])
        return self.receipt(operation,binding,remote)

    def validate_operation(self,operation,binding,remote):
        try:UUID(remote['id'])
        except (ValueError,TypeError,KeyError):raise ReadError('connector_operation_mismatch') from None
        if (remote.get('tenant_id')!=self.client.tenant_id or remote.get('proposal_id')!=binding['proposal_id']
            or remote.get('approval_id')!=binding['approval_id'] or remote.get('idempotency_key')!=operation['id']):
            raise ReadError('connector_operation_mismatch')

    def receipt(self,operation,binding,remote):
        self.validate_operation(operation,binding,remote)
        if remote.get('status')!='verified':return None
        result=remote.get('result');preview=binding['preview']
        digest=hashlib.sha256(canonical(preview).encode()).hexdigest()
        if not isinstance(result,dict) or result.get('operation_id')!=remote['id'] or result.get('payload_hash')!=digest:
            raise ReadError('connector_receipt_mismatch')
        record=result.get('record')
        if (not isinstance(record,dict) or type(record.get('external_id')) is not int or record['external_id']<1
            or any(record.get(k)!=v for k,v in preview.items() if k not in {'source_version','contract_version'})):
            raise ReadError('connector_record_mismatch')
        return {'operation_id':operation['id'],'tenant_id':operation['tenant'],'payload_hash':operation['payload_hash'],
                'external_id':str(record['external_id']),'state':'read_back_verified'}

    def post(self,path,body):
        # One attempt only. On lost response, discover via workspace and read-back.
        try:token=self.client.reader._token()
        except Exception:raise ReadError('credentials_unavailable') from None
        if not isinstance(token,str) or not token or any(c.isspace() for c in token):raise ReadError('credentials_missing')
        try:
            with httpx.Client(transport=self.client.reader.transport,follow_redirects=False,trust_env=False,timeout=20) as client:
                with client.stream('POST',self.client.base+path,headers={'Authorization':'Bearer '+token},json=body) as response:
                    if response.status_code!=200:raise ReadError('connector_write_outcome_unknown')
                    content=bytearray()
                    for chunk in response.iter_bytes():
                        content.extend(chunk)
                        if len(content)>1_048_576:raise ReadError('connector_write_outcome_unknown')
                    data=json.loads(content)
                    if not isinstance(data,dict):raise ReadError('connector_write_outcome_unknown')
                    return data
        except (httpx.HTTPError,ValueError,TypeError):raise ReadError('connector_write_outcome_unknown') from None
