"""Synthetic lab-role approval and real Odoo effect; not a human approval study."""
import json
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import httpx
from backend.config import ROOT
from backend.domain import SalesService, DomainError
from backend.models import Actor, DealInput, SourceInput, ProposalInput, ApprovalInput
from backend.postgres_store import PostgresStore
from backend.read_clients import OdooReadClient
from backend.odoo_effects import OdooActivityAdapter
from backend.bindings import BindingRepository, ConnectorBindingInput
from backend.execution import ExecutionService


def check_odoo(owner, dsn, tenant):
    # Explicit fixture file is supplied by the resource-bounded session runner.
    path=(ROOT/os.environ['SALES_ODOO_LAB_SESSION']).resolve()
    if not path.is_relative_to((ROOT/'local').resolve()):raise ValueError('Session must be local')
    cfg=json.loads(path.read_text())
    client=OdooReadClient(cfg['base_url'],cfg['tenant'],cfg['company_id'],lambda:cfg['operator_token'])
    mapping={'odoo-lab':{'opportunity_id':cfg['opportunity_id'],'assignee_id':cfg['assignee_id']}}
    actors={}
    for role in ('worker','operator','approver'):
        actor=Actor(id=str(uuid4()),tenant_id=str(tenant),role=role,deal_ids={'odoo-lab'})
        owner.execute('INSERT INTO actors(tenant_id,id,role) VALUES(%s,%s,%s)',(tenant,actor.id,role))
        actors[role]=actor
    sales=SalesService(PostgresStore(dsn));now=datetime.now(timezone.utc)
    sales.put_deal(actors['worker'],'odoo-lab',DealInput(account_id='sandbox',title='Synthetic activity',recipient='buyer@example.test',version=1))
    sales.put_source(actors['worker'],'odoo-lab',SourceInput(external_id='source',revision=1,occurred_at=now,text='Please confirm the synthetic demo.'))
    from backend.sales_rules import Commitment
    from backend.skills import SkillService
    from backend.workflows import WorkflowService, EnqueueInput
    sales.commitment(actors['operator'],'odoo-lab',Commitment(id='connected-review',revision=1,
        owner='Sales',description='Project04 lab '+uuid4().hex[:12],due_at=now+timedelta(days=1),observed_at=now,
        evidence={'source_id':'source','revision':1,'quote':'Please confirm the synthetic demo.'}))
    workflows=WorkflowService(sales,SkillService(sales))
    job=workflows.enqueue(actors['worker'],EnqueueInput(deal_id='odoo-lab',deal_version=1,journey='intake',kind='crm',commitment={'id':'connected-review','revision':1}))
    outcome=workflows.tick(actors['worker'],'intake')
    local=sales.get(actors['operator'],outcome['proposal_id'])
    assert local['actor_id']==actors['worker'].id and outcome['status']=='awaiting_approval'
    repo=BindingRepository(sales,actors['operator'])
    adapter=OdooActivityAdapter(client,repo.load,mapping,timezone_name='Asia/Jakarta',write_enabled=True)
    execution=ExecutionService(sales,adapter,enabled=True)
    try:execution.execute(actors['operator'],local['id'],'crm')
    except DomainError as e:assert e.code=='approval_required'
    else:raise AssertionError('Unapproved operation accepted')
    preparation=repo.preparation(local['id'],adapter);preview=preparation['preview']
    with httpx.Client(base_url=cfg['base_url'],trust_env=False,timeout=20) as http:
        headers={'Authorization':'Bearer '+cfg['operator_token']}
        response=http.post('/v1/activities/prepare',headers=headers,json={k:preview[k] for k in ('opportunity_id','assignee_id','due_date','summary')})
        assert response.status_code==201
        remote=response.json()
        assert all(remote['preview'].get(k)==v for k,v in preview.items())
        preview=remote['preview']
        denied=http.post('/v1/proposals/'+remote['id']+'/approve',headers=headers,json={'payload_hash':remote['payload_hash']})
        assert denied.status_code==403
        approved=http.post('/v1/proposals/'+remote['id']+'/approve',headers={'Authorization':'Bearer '+cfg['approver_token']},json={'payload_hash':remote['payload_hash']})
        assert approved.status_code==201
        approval=approved.json();assert approval['approver_id']!=remote['actor_id']
    binding=ConnectorBindingInput(connector_tenant=cfg['tenant'],proposal_id=remote['id'],approval_id=approval['id'],actor_id=remote['actor_id'],preview=preview)
    browser=os.environ.get('SALES_ODOO_BROWSER_PROBE')=='enabled'
    if browser:
        from scripts.odoo_browser_review import review
        review(dsn,actors,cfg,local,binding,'approve')
    else:
        repo.attach(local['id'],binding,adapter)
        sales.approve(actors['approver'],local['id'],ApprovalInput(kind='crm',payload_hash=local['payload_hash']))
    faults=os.environ.get('SALES_ODOO_FAULT_PROBE')=='enabled'
    fault_checks=[]
    if faults:
        from concurrent.futures import ThreadPoolExecutor
        from backend.read_clients import ReadError
        from scripts.odoo_http_faults import check as check_http_faults
        network_checks=check_http_faults(cfg)
        invalid=OdooReadClient(cfg['base_url'],cfg['tenant'],cfg['company_id'],lambda:'invalid-lab-token')
        try:invalid.reader.get(cfg['base_url']+'/v1/opportunities')
        except ReadError as error:assert error.code=='credentials_rejected'
        else:raise AssertionError('Invalid real connector token accepted')
        other=owner.execute('SELECT id FROM tenants WHERE id<>%s LIMIT 1',(tenant,)).fetchone()[0]
        outsider=Actor(id=str(uuid4()),tenant_id=str(other),role='operator',deal_ids={'odoo-lab'})
        owner.execute('INSERT INTO actors(tenant_id,id,role) VALUES(%s,%s,%s)',(other,outsider.id,'operator'))
        try:execution.execute(outsider,local['id'],'crm')
        except DomainError as error:assert error.code=='record_not_found'
        else:raise AssertionError('Foreign tenant accepted')
        clock=sales.clock;sales.clock=lambda:now+timedelta(days=2)
        try:
            try:execution.execute(actors['operator'],local['id'],'crm')
            except DomainError as error:assert error.code=='proposal_expired'
            else:raise AssertionError('Expired approval accepted')
        finally:sales.clock=clock
        assert owner.execute('SELECT count(*) FROM operations WHERE tenant_id=%s',(tenant,)).fetchone()[0]==0
        class LoseSuccessfulResponse:
            calls=0
            def dispatch(self,operation,payload):
                self.calls+=1
                receipt=adapter.dispatch(operation,payload)
                assert receipt['state']=='read_back_verified'
                raise TimeoutError('Injected loss after actual verified remote write')
            def observe(self,operation):return adapter.observe(operation)
        lost=LoseSuccessfulResponse();execution=ExecutionService(sales,lost,enabled=True)
        with ThreadPoolExecutor(max_workers=8) as pool:
            results=list(pool.map(lambda _:execution.execute(actors['operator'],local['id'],'crm'),range(8)))
        assert len({item['id'] for item in results})==1 and lost.calls==1
        first=sales.operation(actors['operator'],results[0]['id'])
        assert first['status']=='unknown'
        repeat=execution.execute(actors['operator'],local['id'],'crm')
        assert repeat['status']=='unknown' and lost.calls==1
        recovered=execution.reconcile(actors['operator'],first['id'])
        assert recovered['status']=='verified' and lost.calls==1
        fault_checks=network_checks+['real_connector_invalid_token_rejected','real_postgres_foreign_tenant_denied_before_effect',
            'injected_clock_expiry_denied_before_effect','eight_concurrent_calls_one_real_odoo_dispatch',
            'injected_lost_success_response_records_unknown','unknown_repeat_never_redispatches',
            'real_odoo_observation_recovers_unknown_to_verified']
    else:
        first=execution.execute(actors['operator'],local['id'],'crm')
        assert first['status']=='verified'
    again=execution.execute(actors['operator'],local['id'],'crm');assert again['id']==first['id']
    observed=execution.reconcile(actors['operator'],first['id']);assert observed['status']=='verified'
    workspace=client.reader.get(cfg['base_url']+'/v1/workspace/proposals/'+remote['id'])
    assert workspace['operation']['idempotency_key']==first['id'] and workspace['operation']['status']=='verified'
    assert owner.execute('SELECT count(*) FROM operations WHERE tenant_id=%s',(tenant,)).fetchone()[0]==1
    if browser:
        review(dsn,actors,cfg,local,binding,'outcome')
        fault_checks+=['real_browser_operator_binding_without_approval_bypass','real_browser_distinct_approver_crm_only','real_browser_verified_odoo_outcome']
    return fault_checks+['operator_binds_pending_worker_proposal_without_ownership_transfer','unapproved_local_effect_denied','connector_operator_self_approval_denied',
            'distinct_lab_approver_bound_exact_preview','real_odoo_activity_read_back_verified',
            'repeat_execute_reuses_one_local_and_remote_operation','reconcile_reads_verified_remote_receipt']
