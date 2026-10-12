import hashlib
import json
import secrets
from pathlib import Path
from backend.domain import SalesService
from backend.models import Actor, DealInput, SourceInput
from backend.store import Store


def seed(service, worker):
    service.put_deal(worker, "deal-1", DealInput(account_id="northstar-lab", title="Northstar 25-seat proposal", recipient="buyer@example.test", version=1))
    service.put_source(worker, "deal-1", SourceInput(external_id="thread-1", revision=1, occurred_at="2026-10-08T10:00:00Z",
        text="Thanks for sharing the revised 25-seat proposal. Please call me on 15 October 2026 at 14:00 Asia/Jakarta to discuss pricing, and email me the call details."))


def main():
    root = Path("local")
    root.mkdir(exist_ok=True)
    identities_path, tokens_path = root / "identities.json", root / "access-tokens.json"
    if identities_path.exists() or tokens_path.exists():
        raise SystemExit("Local identities already exist; refusing to rotate credentials implicitly.")
    tokens = {role: secrets.token_urlsafe(32) for role in ["operator", "approver", "auditor", "worker"]}
    actors = {role: Actor(id=f"demo-{role}", tenant_id="demo", role=role, deal_ids={"deal-1"}) for role in tokens}
    seed(SalesService(Store(root / "sales.sqlite")), actors["worker"])
    identities_path.write_text(json.dumps({hashlib.sha256(token.encode()).hexdigest():actors[role].model_dump(mode="json") for role,token in tokens.items()}, indent=2), encoding="utf-8")
    tokens_path.write_text(json.dumps(tokens, indent=2), encoding="utf-8")
    print("Synthetic demo seeded. Private local access tokens saved in ignored local/access-tokens.json; values are not printed.")


if __name__ == "__main__":
    main()
