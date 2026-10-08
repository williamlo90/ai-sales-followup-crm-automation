"""Persist intent before dispatch. An uncertain dispatch is never retried here."""
import json
from typing import Protocol
from uuid import uuid4
from backend.domain import DomainError, SalesService, canonical, effect_key


class EffectAdapter(Protocol):
    def dispatch(self, operation: dict, payload: dict) -> dict: ...
    def observe(self, operation: dict) -> dict | None: ...


class ExecutionService:
    def __init__(self, sales: SalesService, adapter: EffectAdapter, *, enabled=False,
                 send_enabled=False, recipients: frozenset[str] = frozenset()):
        self.sales, self.adapter = sales, adapter
        self.enabled, self.send_enabled, self.recipients = enabled, send_enabled, recipients

    def load(self, conn, actor, ident):
        row = conn.execute("SELECT * FROM operations WHERE tenant=? AND id=?", (actor.tenant_id, ident)).fetchone()
        if not row:
            raise DomainError("record_not_found",404)
        self.sales.row(conn, actor, row["proposal_id"])
        return dict(row)

    def execute(self, actor, proposal_id: str, kind: str):
        if kind not in {"crm", "email"}:
            raise DomainError("invalid_operation",422)
        if not self.enabled:
            raise DomainError("execution_disabled",403)
        with self.sales.store.connect() as conn:
            proposal = self.sales.row(conn, actor, proposal_id)
            self.sales.scope(actor, proposal["deal_id"], {"operator","worker"})
            self.sales.freshness(conn,actor,proposal)
            payload = json.loads(proposal["payload"])
            approval = conn.execute("SELECT * FROM approvals WHERE tenant=? AND proposal_id=? AND kind=?",
                                    (actor.tenant_id,proposal_id,kind)).fetchone()
            if not approval or approval["payload_hash"] != proposal["payload_hash"]:
                raise DomainError("approval_required",403)
            if kind == "email" and (not self.send_enabled or payload["recipient"] not in self.recipients):
                raise DomainError("send_not_permitted",403)
            # Same source revision/deal/kind is one logical effect, even if prose changes.
            key = effect_key(payload,kind)
            old = self.sales.prior_effect(conn,actor,payload,kind)
            if old:
                original=self.sales.row(conn,actor,old["proposal_id"])
                if payload.get("commitment")!=json.loads(original["payload"]).get("commitment"):
                    raise DomainError("revision_update_requires_review")
                return self.load(conn,actor,old['id'])
            operation = {"tenant":actor.tenant_id,"id":str(uuid4()),"proposal_id":proposal_id,"kind":kind,
                         "effect_key":key,"payload_hash":proposal["payload_hash"],"status":"dispatched","result":None}
            conn.execute("INSERT INTO operations(tenant,id,proposal_id,kind,effect_key,payload_hash,status,result) VALUES(?,?,?,?,?,?,?,?)",tuple(operation.values()))
            self.sales.audit(conn,actor,"operation.dispatched",operation["id"])
        # The committed ledger survives timeout/process exit. No database transaction
        # spans a remote call; a second caller sees dispatched and cannot redispatch.
        try:
            observed = self.adapter.dispatch(operation,payload)
        except Exception:
            observed = None
        return self.record(actor, operation["id"], observed)

    def record(self,actor,ident,observed):
        with self.sales.store.connect() as conn:
            operation = self.load(conn,actor,ident)
            # A late timeout/result must not regress a successful reconciliation.
            if operation["status"] in {"verified","accepted"}:
                return operation
            valid = (isinstance(observed,dict) and observed.get("operation_id")==ident
                     and observed.get("payload_hash")==operation["payload_hash"]
                     and observed.get("tenant_id")==actor.tenant_id
                     and isinstance(observed.get("external_id"),str) and bool(observed["external_id"]))
            status = "unknown"
            if valid:
                if operation["kind"]=="crm" and observed.get("state")=="read_back_verified":
                    status="verified"
                elif operation["kind"]=="email" and observed.get("state") in {"accepted","sent"}:
                    status="accepted" # Neither acceptance nor Sent Items proves delivery/read.
            conn.execute("UPDATE operations SET status=?,result=? WHERE tenant=? AND id=?",
                         (status,canonical(observed) if valid else None,actor.tenant_id,ident))
            self.sales.audit(conn,actor,f"operation.{status}",ident)
            return self.load(conn,actor,ident)

    def reconcile(self,actor,ident):
        if actor.role not in {"operator","worker"}:
            raise DomainError("role_not_permitted",403)
        with self.sales.store.connect() as conn:
            operation = self.load(conn,actor,ident)
        # Observation remains possible after a proposal expires or customer opts out.
        try:
            observed = self.adapter.observe(operation)
        except Exception:
            observed = None
        return self.record(actor,ident,observed)
