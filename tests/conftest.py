import hashlib
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from backend.app import create_app
from backend.domain import SalesService
from backend.models import Actor, DealInput, SourceInput
from backend.store import Store


@pytest.fixture
def lab(tmp_path):
    now = datetime(2026, 10, 8, 12, tzinfo=timezone.utc)
    service = SalesService(Store(tmp_path / "lab.sqlite"), clock=lambda: now)
    actors = {role: Actor(id=role, tenant_id="lab", role=role, deal_ids={"deal-1"})
              for role in ["worker", "operator", "approver", "auditor", "administrator"]}
    actors["outsider"] = Actor(id="outsider", tenant_id="other", role="approver", deal_ids={"deal-1"})
    actors["unscoped"] = Actor(id="unscoped", tenant_id="lab", role="approver", deal_ids={"deal-2"})
    tokens = {hashlib.sha256(key.encode()).hexdigest(): value for key, value in actors.items()}
    service.put_deal(actors["worker"], "deal-1", DealInput(account_id="a-1", title="Demo", recipient="customer@example.test", version=1))
    service.put_source(actors["worker"], "deal-1", SourceInput(external_id="thread-1", revision=1,
        occurred_at="2026-10-08T10:00:00Z", text="Please move the demo to 15 October 2026 at 14:00 Asia/Jakarta."))
    client = TestClient(create_app(service, tokens))
    return service, actors, client


@pytest.fixture
def proposal():
    return {"deal_id": "deal-1", "deal_version": 1,
            "evidence": [{"source_id": "thread-1", "revision": 1, "quote": "15 October 2026 at 14:00 Asia/Jakarta"}],
            "summary": "Confirm rescheduled demo", "due_at": "2026-10-15T14:00:00+07:00",
            "draft": "We have noted the revised demo time: 15 October 2026 at 14:00 Asia/Jakarta."}


def auth(role):
    return {"Authorization": f"Bearer {role}"}
