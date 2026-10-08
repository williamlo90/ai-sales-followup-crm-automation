"""Typed adapter boundaries; implementation and connected status are separate."""
from datetime import datetime
from typing import Literal, Protocol
from pydantic import Field
from backend.models import Contract


class Operation(Contract):
    id: str
    tenant_id: str
    proposal_id: str
    kind: Literal["crm", "email"]
    idempotency_key: str
    status: Literal["prepared", "approved", "dispatched", "accepted", "verified", "unknown", "failed", "review"]
    external_id: str | None = None
    evidence: dict[str, str] = Field(default_factory=dict)
    error_code: str | None = None


class CrmPort(Protocol):
    def context(self, tenant_id: str, deal_id: str) -> dict: ...
    def prepare_activity(self, tenant_id: str, activity: dict) -> dict: ...
    def apply_approved(self, operation: Operation, connector_approval_id: str) -> Operation: ...
    def reconcile(self, operation: Operation) -> Operation: ...


class MailPort(Protocol):
    def messages(self, tenant_id: str, cursor: str | None) -> dict: ...
    def send_approved(self, operation: Operation, draft: dict) -> Operation: ...
    def reconcile(self, operation: Operation) -> Operation: ...


class ModelPort(Protocol):
    def extract(self, sources: list[dict], context: dict) -> dict: ...
    def draft(self, commitments: list[dict], context: dict) -> dict: ...


class SchedulerPort(Protocol):
    def due(self, tenant_id: str, at: datetime, cursor: str | None) -> dict: ...
