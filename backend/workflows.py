"""Durable bounded coordinator; all business decisions delegate to shared core."""
import hashlib
import json
from datetime import timedelta, datetime
from typing import Literal
from uuid import uuid4
from backend.models import Contract, PrepareCommitmentInput
from backend.domain import DomainError, canonical


class EnqueueInput(PrepareCommitmentInput):
    deal_id: str
    journey: Literal['intake','due']
    kind: Literal['crm','email']


class RecoveryInput(Contract):
    action: Literal['observe','renew_expired','recheck']


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

    def list(self,actor):
        if actor.role not in {'worker','operator','approver','auditor'}:raise DomainError('role_not_permitted',403)
        with self.sales.store.connect() as conn:
            rows=conn.execute('SELECT id,deal_id FROM workflow_jobs WHERE tenant=? ORDER BY next_at DESC,id LIMIT 200',(actor.tenant_id,)).fetchall()
        return [self.get(actor,r['id']) for r in rows if r['deal_id'] in actor.deal_ids]

    def recover(self,actor,ident,action):
        if actor.role not in {'operator','worker'}:raise DomainError('role_not_permitted',403)
        with self.sales.store.connect() as conn:
            row=conn.execute('SELECT * FROM workflow_jobs WHERE tenant=? AND id=?',(actor.tenant_id,ident)).fetchone()
            if not row:raise DomainError('record_not_found',404)
            self.sales.scope(actor,row['deal_id'])
            if row['lease_until'] and datetime.fromisoformat(row['lease_until'])>self.sales.clock():raise DomainError('job_busy')
            if row['status'] not in {'review','disabled','unknown'}:raise DomainError('job_not_recoverable')
            operation_id=row['operation_id'];proposal_id=row['proposal_id']
            data=json.loads(row['payload'])
            if proposal_id and not operation_id:
                found=conn.execute('SELECT id FROM operations WHERE tenant=? AND proposal_id=? AND kind=?',
                    (actor.tenant_id,proposal_id,data['kind'])).fetchone()
                if found:operation_id=found['id']
            if action=='observe':
                if not operation_id:raise DomainError('operation_required')
            elif action=='renew_expired':
                if operation_id:raise DomainError('reconciliation_required')
                if row['error_code']!='proposal_expired':raise DomainError('renewal_not_permitted')
                proposal_id=None
            elif action=='recheck':
                if operation_id:raise DomainError('reconciliation_required')
            else:raise DomainError('invalid_recovery',422)
            conn.execute('UPDATE workflow_jobs SET status=?,proposal_id=?,operation_id=?,next_at=?,error_code=NULL,lease_id=NULL,lease_until=NULL WHERE tenant=? AND id=?',
                ('queued',proposal_id,operation_id,self.sales.clock().isoformat(),actor.tenant_id,ident))
            self.sales.audit(conn,actor,'workflow.recovery.'+action,ident)
        return self.get(actor,ident)

    def discover_due(self,actor,kind='email',limit=50):
        self.worker(actor)
        if kind not in {'crm','email'} or type(limit) is not int or not 1<=limit<=100:raise DomainError('invalid_discovery',422)
        with self.sales.store.connect() as conn:
            scan=conn.execute('SELECT cursor FROM workflow_scans WHERE tenant=? AND worker_id=? AND kind=?',(actor.tenant_id,actor.id,kind)).fetchone()
            cursor=json.loads(scan['cursor']) if scan else ['', '']
            rows=conn.execute('SELECT c.deal_id,c.id,c.revision,c.payload,d.payload AS deal FROM commitments c JOIN deals d ON d.tenant=c.tenant AND d.id=c.deal_id WHERE c.tenant=? AND (c.deal_id>? OR (c.deal_id=? AND c.id>?)) AND NOT EXISTS(SELECT 1 FROM commitments newer WHERE newer.tenant=c.tenant AND newer.deal_id=c.deal_id AND newer.id=c.id AND newer.revision>c.revision) ORDER BY c.deal_id,c.id LIMIT ?',
                (actor.tenant_id,cursor[0],cursor[0],cursor[1],limit)).fetchall()
        queued=[]
        for row in rows:
            commitment=json.loads(row['payload']);deal=json.loads(row['deal'])
            if (row['deal_id'] not in actor.deal_ids or commitment['state']!='active' or deal['opt_out'] or deal['deleted']
                or datetime.fromisoformat(commitment['due_at'])>self.sales.clock()):continue
            try:
                job=self.enqueue(actor,EnqueueInput(deal_id=row['deal_id'],deal_version=deal['version'],journey='due',kind=kind,
                    commitment={'id':row['id'],'revision':row['revision']}))
            except DomainError as exc:
                if exc.code=='job_already_owned':continue
                raise
            queued.append(job['id'])
        # Advance only after every enqueue succeeded. Crash replay is idempotent.
        next_cursor=[rows[-1]['deal_id'],rows[-1]['id']] if len(rows)==limit else ['', '']
        with self.sales.store.connect() as conn:
            conn.execute('INSERT INTO workflow_scans VALUES(?,?,?,?) ON CONFLICT(tenant,worker_id,kind) DO UPDATE SET cursor=excluded.cursor',
                (actor.tenant_id,actor.id,kind,canonical(next_cursor)))
        return {'job_ids':queued,'scanned':len(rows),'cycle_complete':len(rows)<limit}

    def tick(self,actor,journey):
        self.worker(actor)
        if journey not in {'intake','due'}:raise DomainError('invalid_journey',422)
        if journey=='due':self.discover_due(actor)
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
            if data['journey']=='due':
                versions=[c for c in self.sales.commitments(actor,data['deal_id']) if c['id']==data['commitment']['id']]
                if not versions:raise DomainError('record_not_found',404)
                latest=max(versions,key=lambda c:c['revision'])
                if latest['revision']!=data['commitment']['revision']:raise DomainError('commitment_changed')
                if latest['state']!='active':raise DomainError('commitment_cancelled')
                if datetime.fromisoformat(latest['due_at'])>self.sales.clock():return {'status':'not_due'}
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
