from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import pytest
from backend.domain import DomainError
from backend.execution import ExecutionService
from backend.models import ApprovalInput, ProposalInput, SourceInput
from doubles import EffectDouble


def approved(lab,proposal,kind="crm"):
    service, actors, _=lab
    p=service.prepare(actors["operator"],ProposalInput(**proposal))
    service.approve(actors["approver"],p["id"],ApprovalInput(kind=kind,payload_hash=p["payload_hash"]))
    return p


def test_lost_response_reconciles_without_duplicate_after_restart(lab,proposal):
    p=approved(lab,proposal)
    double=EffectDouble(lose_response=True)
    executor=ExecutionService(lab[0],double,enabled=True)
    result=executor.execute(lab[1]["operator"],p["id"],"crm")
    assert result["status"]=="unknown"
    restarted=ExecutionService(lab[0],double,enabled=True)
    assert restarted.execute(lab[1]["operator"],p["id"],"crm")["id"]==result["id"]
    now=lab[0].clock()
    lab[0].clock=lambda:now+timedelta(days=2)
    assert restarted.reconcile(lab[1]["operator"],result["id"])["status"]=="verified"
    assert double.calls==len(double.effects)==1


def test_concurrent_execution_one_effect(lab,proposal):
    p=approved(lab,proposal)
    double=EffectDouble()
    executor=ExecutionService(lab[0],double,enabled=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(lambda _:executor.execute(lab[1]["operator"],p["id"],"crm"),range(8)))
    assert len({r["id"] for r in results})==1
    assert double.calls==len(double.effects)==1


def test_new_prose_cannot_duplicate_effect(lab,proposal):
    p=approved(lab,proposal)
    double=EffectDouble()
    executor=ExecutionService(lab[0],double,enabled=True)
    original=executor.execute(lab[1]["operator"],p["id"],"crm")
    proposal["draft"]="Different phrasing of the same follow-up"
    updated=approved(lab,proposal)
    assert executor.execute(lab[1]["operator"],updated["id"],"crm")["id"]==original["id"]
    assert double.calls==1


def test_crm_approval_never_authorizes_send(lab,proposal):
    p=approved(lab,proposal)
    double=EffectDouble()
    executor=ExecutionService(lab[0],double,enabled=True,send_enabled=True,recipients=frozenset({"customer@example.test"}))
    with pytest.raises(DomainError,match="approval_required"):
        executor.execute(lab[1]["operator"],p["id"],"email")
    assert double.calls==0


@pytest.mark.parametrize("send,recipients",[(False,{"customer@example.test"}),(True,set())])
def test_send_requires_switch_and_allowlist(lab,proposal,send,recipients):
    p=approved(lab,proposal,"email")
    double=EffectDouble()
    executor=ExecutionService(lab[0],double,enabled=True,send_enabled=send,recipients=frozenset(recipients))
    with pytest.raises(DomainError,match="send_not_permitted"):
        executor.execute(lab[1]["operator"],p["id"],"email")
    assert not double.effects


def test_sent_is_not_delivered_and_partial_outcomes_stay_separate(lab,proposal):
    p=approved(lab,proposal,"email")
    approved(lab,proposal,"crm")
    double=EffectDouble()
    executor=ExecutionService(lab[0],double,enabled=True,send_enabled=True,recipients=frozenset({"customer@example.test"}))
    assert executor.execute(lab[1]["operator"],p["id"],"crm")["status"]=="verified"
    double.lose_response=True
    email=executor.execute(lab[1]["operator"],p["id"],"email")
    assert email["status"]=="unknown"
    assert executor.reconcile(lab[1]["operator"],email["id"])["status"]=="accepted"
    assert len(double.effects)==2


def test_scope_and_disabled_execution(lab,proposal):
    p=approved(lab,proposal)
    executor=ExecutionService(lab[0],EffectDouble())
    with pytest.raises(DomainError,match="execution_disabled"):
        executor.execute(lab[1]["operator"],p["id"],"crm")
    executor.enabled=True
    with pytest.raises(DomainError,match="record_not_found"):
        executor.execute(lab[1]["outsider"],p["id"],"crm")


def test_wrong_receipt_does_not_close_operation(lab,proposal):
    p=approved(lab,proposal)
    double=EffectDouble(lose_response=True)
    executor=ExecutionService(lab[0],double,enabled=True)
    op=executor.execute(lab[1]["operator"],p["id"],"crm")
    double.effects[op["id"]]["payload_hash"]="wrong"
    assert executor.reconcile(lab[1]["operator"],op["id"])["status"]=="unknown"


def test_new_message_invalidates_previous_approval_before_dispatch(lab,proposal):
    p=approved(lab,proposal)
    lab[0].put_source(lab[1]["worker"],"deal-1",SourceInput(external_id="new-message",revision=1,
        occurred_at="2026-10-08T11:00:00Z",text="Please cancel this follow-up."))
    double=EffectDouble()
    with pytest.raises(DomainError,match="source_changed"):
        ExecutionService(lab[0],double,enabled=True).execute(lab[1]["operator"],p["id"],"crm")
    assert double.calls==0


def test_due_jobs_wait_for_reconciliation_not_redispatch(lab,proposal):
    proposal["due_at"]="2026-10-08T11:00:00Z"
    p=approved(lab,proposal)
    assert lab[0].due(lab[1]["worker"],p["id"],"crm")["eligible"]
    executor=ExecutionService(lab[0],EffectDouble(lose_response=True),enabled=True)
    op=executor.execute(lab[1]["operator"],p["id"],"crm")
    assert lab[0].due(lab[1]["worker"],p["id"],"crm")["reason"]=="reconciliation_required"
    executor.reconcile(lab[1]["operator"],op["id"])
    assert lab[0].due(lab[1]["worker"],p["id"],"crm")["reason"]=="already_completed"
