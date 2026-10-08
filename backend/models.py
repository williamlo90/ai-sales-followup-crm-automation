from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, AwareDatetime


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Actor(Contract):
    id: str
    tenant_id: str
    role: Literal["operator", "approver", "auditor", "administrator", "worker"]
    deal_ids: frozenset[str]


class SourceInput(Contract):
    external_id: str = Field(min_length=1, max_length=200)
    revision: int = Field(ge=1)
    occurred_at: AwareDatetime
    text: str = Field(min_length=1, max_length=50000)


class DealInput(Contract):
    account_id: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=200)
    recipient: str = Field(min_length=3, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    version: int = Field(ge=1)
    opt_out: bool = False
    last_contact_at: AwareDatetime | None = None
    deleted: bool = False


class Evidence(Contract):
    source_id: str = Field(min_length=1, max_length=200)
    revision: int = Field(ge=1)
    quote: str = Field(min_length=1, max_length=4000)


class ProposalInput(Contract):
    deal_id: str = Field(min_length=1, max_length=200)
    deal_version: int = Field(ge=1)
    evidence: list[Evidence] = Field(min_length=1, max_length=20)
    summary: str = Field(min_length=1, max_length=500)
    due_at: AwareDatetime
    draft: str = Field(min_length=1, max_length=10000)


class ApprovalInput(Contract):
    kind: Literal["crm", "email"]
    payload_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class AuditEvent(Contract):
    actor_id: str
    action: str
    resource_id: str
    at: datetime
