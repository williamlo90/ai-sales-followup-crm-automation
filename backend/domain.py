import hashlib
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from backend.models import Actor, ApprovalInput, DealInput, ProposalInput, SourceInput
from backend.store import Store


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class DomainError(Exception):
    def __init__(self, code: str, status: int = 409):
        super().__init__(code)
        self.code, self.status = code, status


class SalesService:
    def __init__(self, store: Store, clock=None):
        self.store = store
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def scope(self, actor: Actor, deal_id: str, roles=None):
        if roles is not None and actor.role not in roles:
            raise DomainError("role_not_permitted", 403)
        if deal_id not in actor.deal_ids:
            raise DomainError("record_not_found", 404)

    def audit(self, conn, actor, action, resource):
        conn.execute("INSERT INTO audit_events(tenant,actor_id,action,resource_id,at) VALUES(?,?,?,?,?)",
                     (actor.tenant_id, actor.id, action, resource, self.clock().isoformat()))

    def put_deal(self, actor: Actor, deal_id: str, data: DealInput):
        # Ingestion is a separate privileged adapter boundary, never an LLM tool.
        self.scope(actor, deal_id, {"worker"})
        payload = data.model_dump(mode="json")
        with self.store.connect() as conn:
            old = conn.execute("SELECT * FROM deals WHERE tenant=? AND id=?", (actor.tenant_id, deal_id)).fetchone()
            if old:
                if data.version == old["version"] and canonical(payload) == old["payload"]:
                    return payload
                if data.version <= old["version"]:
                    raise DomainError("stale_deal_revision")
            conn.execute("INSERT INTO deals VALUES(?,?,?,?) ON CONFLICT(tenant,id) DO UPDATE SET version=excluded.version,payload=excluded.payload",
                         (actor.tenant_id, deal_id, data.version, canonical(payload)))
            self.audit(conn, actor, "deal.ingested", deal_id)
        return payload

    def put_source(self, actor: Actor, deal_id: str, data: SourceInput):
        self.scope(actor, deal_id, {"worker"})
        payload = data.model_dump(mode="json")
        with self.store.connect() as conn:
            if not conn.execute("SELECT 1 FROM deals WHERE tenant=? AND id=?", (actor.tenant_id, deal_id)).fetchone():
                raise DomainError("record_not_found", 404)
            old = conn.execute("SELECT * FROM sources WHERE tenant=? AND id=?", (actor.tenant_id, data.external_id)).fetchone()
            if old:
                if old["deal_id"] != deal_id:
                    raise DomainError("source_link_conflict")
                if data.revision == old["revision"] and canonical(payload) == old["payload"]:
                    return payload
                if data.revision <= old["revision"]:
                    raise DomainError("stale_source_revision")
            conn.execute("INSERT INTO sources VALUES(?,?,?,?,?) ON CONFLICT(tenant,id) DO UPDATE SET revision=excluded.revision,payload=excluded.payload",
                         (actor.tenant_id, data.external_id, data.revision, deal_id, canonical(payload)))
            self.audit(conn, actor, "source.ingested", data.external_id)
        return payload

    def validate(self, conn, actor, payload):
        self.scope(actor, payload["deal_id"])
        row = conn.execute("SELECT * FROM deals WHERE tenant=? AND id=?", (actor.tenant_id, payload["deal_id"])).fetchone()
        if not row:
            raise DomainError("record_not_found", 404)
        deal = json.loads(row["payload"])
        if deal["deleted"]:
            raise DomainError("deal_deleted")
        if row["version"] != payload["deal_version"]:
            raise DomainError("stale_proposal")
        if deal["opt_out"]:
            raise DomainError("customer_opted_out")
        last_contact = datetime.fromisoformat(deal["last_contact_at"]) if deal["last_contact_at"] else None
        for evidence in payload["evidence"]:
            source = conn.execute("SELECT * FROM sources WHERE tenant=? AND id=? AND deal_id=?",
                                  (actor.tenant_id, evidence["source_id"], payload["deal_id"])).fetchone()
            if not source or source["revision"] != evidence["revision"]:
                raise DomainError("source_changed")
            body = json.loads(source["payload"])
            if evidence["quote"] not in body["text"]:
                raise DomainError("unsupported_evidence", 422)
            if last_contact and last_contact >= datetime.fromisoformat(body["occurred_at"]):
                raise DomainError("already_contacted")
        return deal

    def prepare(self, actor: Actor, data: ProposalInput):
        self.scope(actor, data.deal_id, {"operator", "worker"})
        payload = data.model_dump(mode="json")
        # Recipient comes only from the scoped CRM snapshot, not client input.
        with self.store.connect() as conn:
            deal = self.validate(conn, actor, payload)
            payload["recipient"] = deal["recipient"]
            payload["account_id"] = deal["account_id"]
            digest = hashlib.sha256(canonical(payload).encode()).hexdigest()
            existing = conn.execute("SELECT * FROM proposals WHERE tenant=? AND payload_hash=? AND expires_at>? ORDER BY version DESC LIMIT 1", (actor.tenant_id, digest, self.clock().isoformat())).fetchone()
            if existing:
                if existing["actor_id"] != actor.id:
                    # Preserve proposer separation rather than silently transferring ownership.
                    raise DomainError("proposal_already_owned")
                return self.view(conn, actor, existing)
            ident, now = str(uuid4()), self.clock()
            version = conn.execute("SELECT COALESCE(MAX(version),0)+1 FROM proposals WHERE tenant=? AND deal_id=?", (actor.tenant_id, data.deal_id)).fetchone()[0]
            conn.execute("INSERT INTO proposals VALUES(?,?,?,?,?,?,?,?,?)",
                         (actor.tenant_id, ident, data.deal_id, actor.id, canonical(payload), digest,
                          now.isoformat(), (now + timedelta(hours=24)).isoformat(), version))
            self.audit(conn, actor, "proposal.prepared", ident)
            return self.view(conn, actor, self.row(conn, actor, ident))

    def row(self, conn, actor, ident):
        row = conn.execute("SELECT * FROM proposals WHERE tenant=? AND id=?", (actor.tenant_id, ident)).fetchone()
        if not row:
            raise DomainError("record_not_found", 404)
        self.scope(actor, row["deal_id"], {"operator", "approver", "auditor", "worker"})
        return row

    def freshness(self, conn, actor, row):
        if datetime.fromisoformat(row["expires_at"]) <= self.clock():
            raise DomainError("proposal_expired")
        self.validate(conn, actor, json.loads(row["payload"]))

    def view(self, conn, actor, row):
        result = dict(row)
        result.pop("tenant")
        result["payload"] = json.loads(row["payload"])
        result["validation_error"] = None
        try:
            self.freshness(conn, actor, row)
        except DomainError as exc:
            result["validation_error"] = exc.code
        result["approvals"] = [dict(a) for a in conn.execute(
            "SELECT kind,actor_id,payload_hash,created_at FROM approvals WHERE tenant=? AND proposal_id=?",
            (actor.tenant_id, row["id"]))]
        result["status"] = "review_required" if result["validation_error"] else "prepared"
        result["approval_valid"] = bool(result["approvals"]) and not bool(result["validation_error"])
        result["execution_enabled"] = False
        result["draft_validation"] = "human_review_required"
        return result

    def get(self, actor, ident):
        with self.store.connect() as conn:
            return self.view(conn, actor, self.row(conn, actor, ident))

    def list(self, actor):
        if actor.role == "administrator":
            raise DomainError("role_not_permitted", 403)
        with self.store.connect() as conn:
            rows = conn.execute("SELECT * FROM proposals WHERE tenant=? ORDER BY created_at DESC", (actor.tenant_id,)).fetchall()
            return [self.view(conn, actor, row) for row in rows if row["deal_id"] in actor.deal_ids][:100]

    def approve(self, actor: Actor, ident: str, data: ApprovalInput):
        if actor.role != "approver":
            raise DomainError("role_not_permitted", 403)
        with self.store.connect() as conn:
            row = self.row(conn, actor, ident)
            if row["actor_id"] == actor.id:
                raise DomainError("self_approval", 403)
            self.freshness(conn, actor, row)
            if data.payload_hash != row["payload_hash"]:
                raise DomainError("payload_changed")
            existing = conn.execute("SELECT 1 FROM approvals WHERE tenant=? AND proposal_id=? AND kind=?",
                                    (actor.tenant_id, ident, data.kind)).fetchone()
            if not existing:
                conn.execute("INSERT INTO approvals VALUES(?,?,?,?,?,?)", (actor.tenant_id, ident, data.kind,
                             actor.id, data.payload_hash, self.clock().isoformat()))
                self.audit(conn, actor, f"approval.{data.kind}", ident)
            return self.view(conn, actor, row)
