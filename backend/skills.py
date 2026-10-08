"""One application skill binding shared by API, MCP and workflow callers."""
import json
import time
from uuid import uuid4
from pydantic import Field
from backend.models import Contract, PrepareCommitmentInput
from backend.domain import DomainError
from backend.providers import ModelAdapter, ProviderError, PROMPT_VERSION, SCHEMA_VERSION
from backend.skill_outputs import OUTPUTS


class ExtractInput(Contract):
    deal_id: str = Field(min_length=1,max_length=200)


class PrepareInput(PrepareCommitmentInput):
    deal_id: str = Field(min_length=1,max_length=200)


class DraftInput(Contract):
    proposal_id: str = Field(min_length=1,max_length=200)


class ReconcileInput(Contract):
    operation_id: str = Field(min_length=1,max_length=200)


INPUTS={'extract_commitments':ExtractInput,'prepare_crm_update':PrepareInput,'draft_followup':DraftInput,'reconcile_followup':ReconcileInput}


class SkillService:
    version='1.0'
    def __init__(self,sales,model: ModelAdapter | None=None,execution=None):
        self.sales,self.model,self.execution=sales,model,execution

    def invoke(self,actor,name,raw):
        if name not in INPUTS:raise DomainError('skill_not_found',404)
        data=INPUTS[name].model_validate(raw)
        result=getattr(self,name)(actor,data)
        try:
            result=OUTPUTS[name].model_validate(result).model_dump(mode='json')
        except Exception:
            raise DomainError('skill_output_invalid',503) from None
        return {'skill':name,'version':self.version,'result':result}

    def extract_commitments(self,actor,data):
        self.sales.scope(actor,data.deal_id,{'operator','worker'})
        if self.model is None:raise DomainError('model_not_configured',503)
        with self.sales.store.connect() as conn:
            if not conn.execute('SELECT 1 FROM deals WHERE tenant=? AND id=?',(actor.tenant_id,data.deal_id)).fetchone():
                raise DomainError('record_not_found',404)
        started=time.monotonic()
        run_id=str(uuid4())
        metadata={'provider':self.model.profile.provider,'model':self.model.profile.model,
                  'prompt_version':PROMPT_VERSION,'schema_version':SCHEMA_VERSION,'outcome':'started'}
        with self.sales.store.connect() as conn:
            conn.execute('INSERT INTO model_runs VALUES(?,?,?,?,?)',(actor.tenant_id,run_id,actor.id,data.deal_id,json.dumps(metadata)))
        try:
            result=self._extract_commitments(actor,data)
            metadata.update(result['trace'])
            result['run_id']=run_id
            return result
        except (DomainError,ProviderError) as exc:
            metadata['outcome']='rejected'
            metadata['error_code']=exc.code if isinstance(exc,DomainError) else str(exc)
            raise
        finally:
            metadata['total_latency_ms']=round((time.monotonic()-started)*1000,2)
            with self.sales.store.connect() as conn:
                conn.execute('UPDATE model_runs SET metadata=? WHERE tenant=? AND id=?',(json.dumps(metadata),actor.tenant_id,run_id))

    def _extract_commitments(self,actor,data):
        self.sales.scope(actor,data.deal_id,{'operator','worker'})
        if self.model is None:raise DomainError('model_not_configured',503)
        with self.sales.store.connect() as conn:
            deal=conn.execute('SELECT payload FROM deals WHERE tenant=? AND id=?',(actor.tenant_id,data.deal_id)).fetchone()
            if not deal:raise DomainError('record_not_found',404)
            sources=[json.loads(r['payload']) for r in conn.execute('SELECT payload FROM sources WHERE tenant=? AND deal_id=? ORDER BY id',(actor.tenant_id,data.deal_id))]
        if not sources:raise DomainError('source_missing',422)
        context=json.loads(deal['payload'])
        # Only scoped business fields, never tokens, tenant admin config or arbitrary SQL.
        result,trace=self.model.extract(sources,{'account_id':context['account_id'],'deal_id':data.deal_id,
            'title':context['title'],'commitment_history':self.sales.commitments(actor,data.deal_id)})
        source_map={s['external_id']:s for s in sources}
        for commitment in result.commitments:
            evidence=commitment.evidence
            source=source_map.get(evidence.source_id)
            if not source or evidence.revision!=source['revision'] or evidence.quote not in source['text']:
                raise DomainError('model_unsupported_evidence',422)
            from datetime import datetime
            if commitment.observed_at!=datetime.fromisoformat(source['occurred_at']):
                raise DomainError('model_source_timestamp_mismatch',422)
        # Re-read versions after model latency; a successful response can already be stale.
        with self.sales.store.connect() as conn:
            current=self.sales.source_snapshot(conn,actor,data.deal_id)
            expected=sorted([{'id':s['external_id'],'revision':s['revision']} for s in sources],key=lambda x:x['id'])
            current_deal=conn.execute('SELECT payload FROM deals WHERE tenant=? AND id=?',(actor.tenant_id,data.deal_id)).fetchone()
            if current!=expected or not current_deal or json.loads(current_deal['payload'])!=context:
                raise DomainError('context_changed')
        return {'extraction':result.model_dump(mode='json'),'trace':trace,'review_required':True}

    def prepare_crm_update(self,actor,data):
        return self.sales.prepare_commitment(actor,data.deal_id,PrepareCommitmentInput(commitment=data.commitment,deal_version=data.deal_version))

    def draft_followup(self,actor,data):
        proposal=self.sales.get(actor,data.proposal_id)
        if proposal['validation_error']:raise DomainError(proposal['validation_error'])
        return {'proposal_id':proposal['id'],'payload_hash':proposal['payload_hash'],
                'recipient':proposal['payload']['recipient'],'draft':proposal['payload']['draft'],
                'review_required':True,'send_enabled':False}

    def reconcile_followup(self,actor,data):
        # Verify scope even when no adapter is configured.
        existing=self.sales.operation(actor,data.operation_id)
        if self.execution is None:
            return {**existing,'observation':'stored_only','adapter_available':False}
        self.execution.reconcile(actor,data.operation_id)
        return {**self.sales.operation(actor,data.operation_id),'observation':'adapter_read_back','adapter_available':True}
