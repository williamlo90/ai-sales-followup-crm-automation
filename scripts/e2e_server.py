"""Isolated, temporary loopback-only browser fixture server. Never deployed."""
import hashlib
import tempfile
from pathlib import Path
import uvicorn
from backend.app import create_app
from backend.domain import SalesService
from backend.models import Actor
from backend.store import Store
from scripts.seed_demo import seed


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="sales-browser-") as directory:
        actors = {role: Actor(id=role,tenant_id="browser-test",role=role,deal_ids={"deal-1"}) for role in ["operator","approver","worker"]}
        service = SalesService(Store(Path(directory) / "test.sqlite"))
        seed(service, actors["worker"])
        identities = {hashlib.sha256(f"test-only-{role}".encode()).hexdigest():actor for role,actor in actors.items()}
        intake_actors = {role: Actor(id=role,tenant_id="browser-intake",role=role,deal_ids={"deal-1"}) for role in ["operator","worker"]}
        seed(service, intake_actors["worker"])
        identities.update({hashlib.sha256(f"intake-test-{role}".encode()).hexdigest(): actor for role,actor in intake_actors.items()})
        binding_actors = {role: Actor(id=role,tenant_id="browser-binding",role=role,deal_ids={"deal-1"}) for role in ["operator","worker"]}
        seed(service, binding_actors["worker"])
        identities.update({hashlib.sha256(f"binding-test-{role}".encode()).hexdigest(): actor for role,actor in binding_actors.items()})
        uvicorn.run(create_app(service,identities),host="127.0.0.1",port=8040,access_log=False)
