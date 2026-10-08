"""Durable bounded coordinator; all business decisions delegate to shared core."""
import hashlib
import json
from datetime import timedelta
from typing import Literal
from uuid import uuid4
from backend.models import Contract, PrepareCommitmentInput
from backend.domain import DomainError, canonical


class EnqueueInput(PrepareCommitmentInput):
    deal_id: str
    journey: Literal['intake','due']
    kind: Literal['crm','email']


class WorkflowService:
    def __init__(self,sales,skills,execution=None):self.sales,self.skills,self.execution=sales,skills,execution

    def worker(self,actor):
        if actor.role!='worker':raise DomainError('role_not_permitted',403)

    def enqueue(self,actor,data):
        self.worker(actor);self.sales.scope(actor,data.deal_id)
        payload=data.model_dump(mode='json')
        ident=hashlib.sha256(canonical(payload).encode()).hexdigest()
        with self.sales.store.connect() as conn:
            if not conn.execute('SELECT 1 FROM deals WHERE tenant=? AND id=?',(actor.tenant_id,data.deal_id)).fetchone():raise DomainError('record_not_found',404)
            old=conn.execute('SELECT worker_id FROM workflow_jobs WHERE tenant=? AND id=?',(actor.tenant_id,ident)).fetchone()
            if old and old['worker_id']!=actor.id:raise DomainError('job_already_owned')
            if not old:
                conn.execute('INSERT INTO workflow_jobs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    (actor.tenant_id,ident,actor.id,data.deal_id,data.journey,canonical(payload),'queued',None,None,self.sales.clock().isoformat(),None,None,None))
                self.sales.audit(conn,actor,'workflow.enqueued',ident)
        return self.get(actor,ident)

    def get(self,actor,ident):
        with self.sales.store.connect() as conn:
            row=conn.execute('SELECT * FROM workflow_jobs WHERE tenant=? AND id=?',(actor.tenant_id,ident)).fetchone()
            if not row:raise DomainError('record_not_found',404)
            self.sales.scope(actor,row['deal_id'],{'worker','operator','approver','auditor'})
            return {k:row[k] for k in ['id','deal_id','journey','status','proposal_id','operation_id','next_at','error_code']}

    def tick(self,actor,journey):
        self.worker(actor)
        if journey not in {'intake','due'}:raise DomainError('invalid_journey',422)
        now=self.sales.clock();lease=str(uuid4())
        with self.sales.store.connect() as conn:
            rows=conn.execute("SELECT * FROM workflow_jobs WHERE tenant=? AND worker_id=? AND journey=? AND status NOT IN ('completed','review') AND next_at<=? AND (lease_until IS NULL OR lease_until<=?) ORDER BY next_at,id LIMIT 100",
                (actor.tenant_id,actor.id,journey,now.isoformat(),now.isoformat())).fetchall()
            row=next((r for r in rows if r['deal_id'] in actor.deal_ids),None)
            if row is None:return {'status':'idle','needs_poll':False,'job_id':None}
            job=dict(row)
            conn.execute('UPDATE workflow_jobs SET lease_id=?,lease_until=? WHERE tenant=? AND id=?',
                (lease,(now+timedelta(minutes=2)).isoformat(),actor.tenant_id,job['id']))
        try:
            result=self.advance(actor,job)
        except DomainError as exc:
            result={'status':'review','error_code':exc.code}
        # Unexpected crashes leave a recoverable lease; never infer completion.
        with self.sales.store.connect() as conn:
            updated=conn.execute('UPDATE workflow_jobs SET status=?,proposal_id=?,operation_id=?,error_code=?,next_at=?,lease_id=NULL,lease_until=NULL WHERE tenant=? AND id=? AND lease_id=?',
                (result['status'],result.get('proposal_id',job['proposal_id']),result.get('operation_id',job['operation_id']),result.get('error_code'),
                 (self.sales.clock()+timedelta(seconds=60)).isoformat(),actor.tenant_id,job['id'],lease))
            if updated.rowcount!=1:raise DomainError('workflow_lease_changed')
            self.sales.audit(conn,actor,'workflow.'+result['status'],job['id'])
        return {**self.get(actor,job['id']),'job_id':job['id'],'needs_poll':result['status'] in {'awaiting_approval','not_due','unknown'}}

    def advance(self,actor,job):
        data=json.loads(job['payload'])
        if job['proposal_id'] is None:
            prepared=self.skills.invoke(actor,'prepare_crm_update',{k:data[k] for k in ['deal_id','deal_version','commitment']})['result']
            return {'status':'awaiting_approval','proposal_id':prepared['id']}
        if job['operation_id']:
            if self.execution is None:return {'status':'disabled'}
            self.execution.reconcile(actor,job['operation_id'])
            operation=self.sales.operation(actor,job['operation_id'])
            return {'status':'completed' if operation['status'] in {'accepted','verified'} else 'review',
                    'error_code':None if operation['status'] in {'accepted','verified'} else 'reconciliation_required'}
        existing=[o for o in self.sales.proposal_operations(actor,job['proposal_id']) if o['kind']==data['kind']]
        if existing:
            # Recover a crash after ledger commit but before job checkpoint.
            recovered={**job,'operation_id':existing[0]['id']}
            return {**self.advance(actor,recovered),'operation_id':existing[0]['id']}
        proposal=self.sales.get(actor,job['proposal_id'])
        if proposal['validation_error']:raise DomainError(proposal['validation_error'])
        if not any(a['kind']==data['kind'] for a in proposal['approvals']):return {'status':'awaiting_approval'}
        if data['journey']=='due' or data['kind']=='email':
            due=self.sales.due(actor,proposal['id'],data['kind'])
            if not due['eligible']:
                if due['reason']=='not_due':return {'status':'not_due'}
                raise DomainError(due['reason'])
        if self.execution is None:return {'status':'disabled'}
        operation=self.execution.execute(actor,proposal['id'],data['kind'])
        return {'status':'completed' if operation['status'] in {'accepted','verified'} else 'unknown','operation_id':operation['id']}
