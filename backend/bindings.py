"""Immutable connector binding, validated remotely then rechecked locally."""
import json
import sqlite3
from backend.postgres_store import StorageIntegrityError
from typing import Literal
from uuid import UUID
from pydantic import Field
from backend.models import Contract
from backend.domain import DomainError, canonical


class ActivityBindingPreview(Contract):
    kind: Literal['activity']
    company_id: int = Field(gt=0)
    opportunity_id: int = Field(gt=0)
    assignee_id: int = Field(gt=0)
    due_date: str = Field(pattern=r'^\d{4}-\d{2}-\d{2}$')
    summary: str = Field(min_length=1,max_length=120)
    source_version: str = Field(min_length=1,max_length=200)
    contract_version: Literal['1.0']


class ConnectorBindingInput(Contract):
    connector_tenant: UUID
    proposal_id: UUID
    approval_id: UUID
    actor_id: UUID
    preview: ActivityBindingPreview


class BindingRepository:
    def __init__(self,sales,actor):
        if actor.role not in {'operator','worker','approver','auditor'}:raise DomainError('role_not_permitted',403)
        self.sales,self.actor=sales,actor

    def payload(self,tenant,proposal_id):
        if tenant!=self.actor.tenant_id:raise DomainError('record_not_found',404)
        with self.sales.store.connect(self.actor) as conn:
            return json.loads(self.sales.row(conn,self.actor,proposal_id)['payload'])

    def load(self,tenant,proposal_id):
        if tenant!=self.actor.tenant_id:raise DomainError('record_not_found',404)
        with self.sales.store.connect(self.actor) as conn:
            self.sales.row(conn,self.actor,proposal_id)
            row=conn.execute('SELECT payload FROM connector_bindings WHERE tenant=? AND proposal_id=?',(tenant,proposal_id)).fetchone()
            if not row:raise DomainError('connector_binding_missing',409)
            return json.loads(row['payload'])

    def preparation(self,proposal_id,adapter):
        with self.sales.store.connect(self.actor) as conn:
            row=self.sales.row(conn,self.actor,proposal_id)
            self.sales.freshness(conn,self.actor,row)
            digest=row['payload_hash'];payload=json.loads(row['payload'])
        result=adapter.preparation(payload)
        with self.sales.store.connect(self.actor) as conn:
            current=self.sales.row(conn,self.actor,proposal_id)
            self.sales.freshness(conn,self.actor,current)
            if current['payload_hash']!=digest:raise DomainError('payload_changed')
        return {**result,'local_payload_hash':digest}

    def attach(self,proposal_id,data:ConnectorBindingInput,adapter):
        if self.actor.role not in {'operator','worker'}:raise DomainError('role_not_permitted',403)
        with self.sales.store.connect(self.actor) as conn:
            proposal=self.sales.row(conn,self.actor,proposal_id)
            self.sales.freshness(conn,self.actor,proposal)
            self.check_binding_reviewer(conn,proposal)
            local_hash=proposal['payload_hash'];payload=json.loads(proposal['payload'])
        candidate={**data.model_dump(mode='json'),'local_payload_hash':local_hash}
        if candidate['connector_tenant']!=adapter.client.tenant_id:raise DomainError('connector_scope_mismatch',403)
        # This path only reads the connector. Human approval is obtained in #2.
        adapter.validate_activity(payload,candidate)
        workspace=adapter.workspace(candidate,check_expiry=True)
        if workspace.get('operation') is not None:raise DomainError('connector_already_executed')
        with self.sales.store.connect(self.actor) as conn:
            current=self.sales.row(conn,self.actor,proposal_id)
            self.sales.freshness(conn,self.actor,current)
            self.check_binding_reviewer(conn,current)
            if current['payload_hash']!=local_hash:raise DomainError('payload_changed')
            existing=conn.execute('SELECT payload FROM connector_bindings WHERE tenant=? AND proposal_id=?',
                                  (self.actor.tenant_id,proposal_id)).fetchone()
            if existing:
                if json.loads(existing['payload'])!=candidate:raise DomainError('connector_binding_immutable')
                return candidate
            try:
                conn.execute('INSERT INTO connector_bindings VALUES(?,?,?,?,?)',
                    (self.actor.tenant_id,proposal_id,candidate['connector_tenant'],candidate['proposal_id'],canonical(candidate)))
            except (sqlite3.IntegrityError, StorageIntegrityError):raise DomainError('connector_proposal_already_bound') from None
            self.sales.audit(conn,self.actor,'connector.binding_attached',proposal_id)
        return candidate

    def check_binding_reviewer(self,conn,proposal):
        if proposal['actor_id']==self.actor.id:return
        # An operator may finish a worker's pending review through the UI.
        # The durable job establishes delegation; unrelated proposals retain
        # the owner-only rule. row() has already checked tenant/deal scope.
        if self.actor.role=='operator':
            job=conn.execute("SELECT id FROM workflow_jobs WHERE tenant=? AND proposal_id=? AND worker_id=? AND deal_id=? AND status='awaiting_approval'",
                (self.actor.tenant_id,proposal['id'],proposal['actor_id'],proposal['deal_id'])).fetchone()
            if job:return
        raise DomainError('proposal_owner_required',403)
