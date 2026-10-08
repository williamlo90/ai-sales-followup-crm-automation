from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import pytest
from backend.domain import SalesService
from backend.models import Actor, ApprovalInput, DealInput, ProposalInput, SourceInput
from backend.store import Store
from conftest import auth


def prepare(lab, proposal):
    response = lab[2].post("/v1/proposals", json=proposal, headers=auth("operator"))
    assert response.status_code == 201, response.text
    return response.json()


def test_separate_approvals_and_restart(lab, proposal):
    service, actors, client = lab
    p = prepare(lab, proposal)
    for kind in ["crm", "email"]:
        response = client.post(f"/v1/proposals/{p['id']}/approvals", headers=auth("approver"),
                               json={"kind": kind, "payload_hash": p["payload_hash"]})
        assert response.status_code == 200
        if kind == "crm":
            assert [a["kind"] for a in response.json()["approvals"]] == ["crm"]
    restarted = SalesService(Store(service.store.path), service.clock)
    saved = restarted.get(actors["auditor"], p["id"])
    assert len(saved["approvals"]) == 2
    assert saved["execution_enabled"] is False


@pytest.mark.parametrize("role,expected", [(None, 401), ("unknown", 401), ("auditor", 403), ("approver", 403), ("administrator", 403)])
def test_unauthorized_prepare(lab, proposal, role, expected):
    response = lab[2].post("/v1/proposals", json=proposal, headers=auth(role) if role else {})
    assert response.status_code == expected


@pytest.mark.parametrize("role,expected", [("operator", 403), ("worker", 403), ("administrator", 403), ("outsider", 404), ("unscoped", 404)])
def test_approval_scope(lab, proposal, role, expected):
    p = prepare(lab, proposal)
    result = lab[2].post(f"/v1/proposals/{p['id']}/approvals", headers=auth(role), json={"kind":"crm", "payload_hash":p["payload_hash"]})
    assert result.status_code == expected


def test_self_approval_with_changed_role(lab, proposal):
    p = prepare(lab, proposal)
    actor = lab[1]["operator"].model_copy(update={"role": "approver"})
    with pytest.raises(Exception, match="self_approval"):
        lab[0].approve(actor, p["id"], ApprovalInput(kind="crm", payload_hash=p["payload_hash"]))


@pytest.mark.parametrize("change,code", [("source", "source_changed"), ("deal", "stale_proposal"), ("expired", "proposal_expired")])
def test_stale_approval_invalidated(lab, proposal, change, code):
    service, actors, client = lab
    p = prepare(lab, proposal)
    service.approve(actors["approver"], p["id"], ApprovalInput(kind="crm", payload_hash=p["payload_hash"]))
    if change == "source":
        service.put_source(actors["worker"], "deal-1", SourceInput(external_id="thread-1", revision=2, occurred_at="2026-10-08T11:00:00Z", text="Cancel the demo."))
    elif change == "deal":
        service.put_deal(actors["worker"], "deal-1", DealInput(account_id="a-1", title="Changed", recipient="customer@example.test", version=2))
    else:
        previous = service.clock()
        service.clock = lambda: previous + timedelta(days=2)
    result = service.get(actors["operator"], p["id"])
    assert result["validation_error"] == code
    assert result["approval_valid"] is False
    response = client.post(f"/v1/proposals/{p['id']}/approvals", headers=auth("approver"), json={"kind":"email", "payload_hash":p["payload_hash"]})
    assert response.status_code == 409


def test_concurrent_duplicate_proposals(lab, proposal):
    service, actors, _ = lab
    with ThreadPoolExecutor(max_workers=4) as pool:
        result = list(pool.map(lambda _: service.prepare(actors["operator"], ProposalInput(**proposal)), range(8)))
    assert len({p["id"] for p in result}) == 1
    with service.store.connect() as conn:
        assert conn.execute("SELECT count(*) FROM proposals").fetchone()[0] == 1
        assert conn.execute("SELECT count(*) FROM audit_events WHERE action='proposal.prepared'").fetchone()[0] == 1


@pytest.mark.parametrize("field,value", [("tenant_id", "other"), ("recipient", "attacker@example.test"), ("approved", True)])
def test_untrusted_authority_fields_rejected(lab, proposal, field, value):
    proposal[field] = value
    response = lab[2].post("/v1/proposals", json=proposal, headers=auth("operator"))
    assert response.status_code == 422
    assert response.json() == {"error": "invalid_input"}


def test_quote_must_exist_in_scoped_source(lab, proposal):
    proposal["evidence"][0]["quote"] = "Customer approved a discount"
    response = lab[2].post("/v1/proposals", json=proposal, headers=auth("operator"))
    assert response.status_code == 422
    assert response.json()["error"] == "unsupported_evidence"


@pytest.mark.parametrize("change,code", [({"opt_out":True}, "customer_opted_out"), ({"deleted":True}, "deal_deleted"), ({"last_contact_at":"2026-10-08T11:00:00Z"}, "already_contacted")])
def test_contact_eligibility(lab, proposal, change, code):
    service, actors, client = lab
    service.put_deal(actors["worker"], "deal-1", DealInput(account_id="a-1", title="Demo", recipient="customer@example.test", version=2, **change))
    proposal["deal_version"] = 2
    response = client.post("/v1/proposals", json=proposal, headers=auth("operator"))
    assert response.status_code == 409
    assert response.json()["error"] == code


def test_cross_tenant_reads_hidden(lab, proposal):
    p = prepare(lab, proposal)
    client = lab[2]
    assert client.get(f"/v1/proposals/{p['id']}", headers=auth("outsider")).status_code == 404
    assert client.get("/v1/proposals", headers=auth("outsider")).json() == {"items": []}


def test_ingestion_requires_worker(lab):
    response = lab[2].put("/v1/ingest/deals/deal-1", headers=auth("operator"),
        json={"account_id":"a-1", "title":"Demo", "recipient":"test@example.test", "version":2})
    assert response.status_code == 403


def test_source_revision_cannot_regress_or_change_in_place(lab):
    service, actors, _ = lab
    with pytest.raises(Exception, match="stale_source_revision"):
        service.put_source(actors["worker"], "deal-1", SourceInput(external_id="thread-1", revision=1,
            occurred_at="2026-10-08T10:00:00Z", text="Replace without revision"))


def test_timezone_required_and_no_input_echo(lab, proposal):
    proposal["due_at"] = "2026-10-15T14:00:00"
    proposal["draft"] = "sensitive body"
    response = lab[2].post("/v1/proposals", json=proposal, headers=auth("operator"))
    assert response.status_code == 422
    assert "sensitive" not in response.text


def test_wrong_hash_and_unknown_send_endpoint(lab, proposal):
    p = prepare(lab, proposal)
    result = lab[2].post(f"/v1/proposals/{p['id']}/approvals", headers=auth("approver"), json={"kind":"crm", "payload_hash":"0"*64})
    assert result.status_code == 409
    assert lab[2].post(f"/v1/proposals/{p['id']}/send", headers=auth("operator")).status_code == 404


def test_expired_proposal_can_be_renewed_without_reusing_approval(lab, proposal):
    service, actors, _ = lab
    p = prepare(lab, proposal)
    assert p["approval_valid"] is False
    service.approve(actors["approver"], p["id"], ApprovalInput(kind="crm", payload_hash=p["payload_hash"]))
    now = service.clock()
    service.clock = lambda: now + timedelta(days=2)
    renewed = service.prepare(actors["operator"], ProposalInput(**proposal))
    assert renewed["id"] != p["id"]
    assert renewed["version"] == p["version"] + 1
    assert renewed["approvals"] == []
