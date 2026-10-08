import json
from datetime import datetime
from pathlib import Path
import pytest
from backend.models import Actor, DealInput, SourceInput
from backend.sales_rules import Commitment, match_deal, merge_commitment, due_eligibility
from conftest import auth

FIXTURES=json.loads((Path(__file__).parents[1]/"fixtures/rules-v1.json").read_text())


@pytest.mark.parametrize("case",FIXTURES["matching"],ids=lambda c:c["id"])
def test_matching_fixtures(case):
    result=match_deal(case["candidates"],case["account_id"],case.get("explicit"))
    assert result["status"]==case["expected"]
    assert result["deal_id"]==case["deal"]


@pytest.mark.parametrize("case",FIXTURES["due"],ids=lambda c:c["id"])
def test_due_fixtures(case):
    args={key:value for key,value in case.items() if key not in {"id","expected"}}
    for key in ["due_at","now","last_contact","source_at"]:
        if args[key]:args[key]=datetime.fromisoformat(args[key])
    result=due_eligibility(**args)
    assert result["reason"]==case["expected"]
    assert result["eligible"]==(case["expected"]=="due_and_approved")


def candidate(**updates):
    return Commitment.model_validate({"id":"demo-date","revision":1,"owner":"sales","description":"Demo",
        "due_at":"2026-10-14T10:00:00+07:00","observed_at":"2026-10-08T10:00:00Z",
        "evidence":{"source_id":"thread-1","revision":1,"quote":"15 October 2026 at 14:00 Asia/Jakarta"},**updates})


def test_commitment_revised_then_cancelled_preserves_history():
    first=candidate()
    second=candidate(revision=2,supersedes=1,due_at="2026-10-15T14:00:00+07:00",observed_at="2026-10-08T11:00:00Z")
    assert merge_commitment([first],second)["current"].due_at==second.due_at
    cancelled=candidate(revision=3,supersedes=2,state="cancelled",observed_at="2026-10-08T12:00:00Z")
    assert merge_commitment([first,second],cancelled)["current"].state=="cancelled"
    assert merge_commitment([first,second],first)["current"]==second
    assert first.revision==1


@pytest.mark.parametrize("updates,reason",[({"description":"Competing same revision"},"competing_revision"),
    ({"revision":3,"supersedes":1},"missing_predecessor"),
    ({"revision":2,"supersedes":1,"observed_at":"2026-10-07T10:00:00Z"},"chronology_conflict")])
def test_conflicting_revisions_require_review(updates,reason):
    result=merge_commitment([candidate()],candidate(**updates))
    assert result["status"]=="conflict"
    assert result["reason"]==reason


def test_api_scopes_matching_and_evidence(lab):
    service,actors,client=lab
    assert client.get('/v1/deals/match?account_id=a-1',headers=auth('operator')).json()['deal_id']=='deal-1'
    assert client.get('/v1/deals/match?account_id=a-1',headers=auth('outsider')).json()['status']=='review'
    payload=candidate().model_dump(mode="json")
    result=client.post('/v1/deals/deal-1/commitments',headers=auth('operator'),json=payload)
    assert result.status_code==200
    assert result.json()['status']=='applied'
    repeat=client.post('/v1/deals/deal-1/commitments',headers=auth('operator'),json=payload)
    assert repeat.json()['status']=='duplicate'
    history=client.get('/v1/deals/deal-1/commitments',headers=auth('auditor')).json()['items']
    assert len(history)==1
    payload['observed_at']='2026-10-09T01:00:00Z'
    assert client.post('/v1/deals/deal-1/commitments',headers=auth('operator'),json=payload).json()['error']=='source_timestamp_mismatch'


def test_matching_does_not_guess_between_two_deals(lab):
    service,actors,_=lab
    worker=actors['worker'].model_copy(update={'deal_ids':frozenset({'deal-1','deal-2'})})
    service.put_deal(worker,'deal-2',DealInput(account_id='a-1',title='Second deal',recipient='customer@example.test',version=1))
    operator=actors['operator'].model_copy(update={'deal_ids':worker.deal_ids})
    assert service.match(operator,'a-1')['reason']=='ambiguous_deal'
    assert service.match(operator,'a-1','deal-2')['deal_id']=='deal-2'
