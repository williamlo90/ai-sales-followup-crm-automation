"""Validated skill results; exported unchanged for protocol callers."""
from typing import Literal
from pydantic import AwareDatetime
from backend.models import Contract, ProposalInput, DealInput, SourceInput
from backend.sales_rules import Commitment


class ContextView(Contract):
    deal_id: str
    deal: DealInput
    sources: list[SourceInput]
    commitments: list[Commitment]
from backend.providers import Extraction


class SourceRevision(Contract):
    id: str
    revision: int


class ProposalPayload(ProposalInput):
    recipient: str
    account_id: str
    source_snapshot: list[SourceRevision]


class ApprovalView(Contract):
    kind: Literal['crm','email']
    actor_id: str
    payload_hash: str
    created_at: AwareDatetime


class ProposalView(Contract):
    id: str
    deal_id: str
    actor_id: str
    payload: ProposalPayload
    payload_hash: str
    created_at: AwareDatetime
    expires_at: AwareDatetime
    version: int
    validation_error: str | None
    approvals: list[ApprovalView]
    status: Literal['prepared','review_required']
    approval_valid: bool
    execution_enabled: Literal[False]
    draft_validation: Literal['human_review_required']


class Trace(Contract):
    provider: Literal['openai','claude','grok','ollama']
    model: str
    prompt_version: str
    schema_version: str
    schema_hash: str
    latency_ms: float
    usage: dict[str,int]
    cost_usd: float | None
    validation: Literal['contract-double','provider-response']
    outcome: Literal['ready','review']


class ExtractResult(Contract):
    extraction: Extraction
    trace: Trace
    review_required: Literal[True]
    run_id: str


class DraftResult(Contract):
    proposal_id: str
    payload_hash: str
    recipient: str
    draft: str
    review_required: Literal[True]
    send_enabled: Literal[False]


class Receipt(Contract):
    operation_id: str
    payload_hash: str
    tenant_id: str
    external_id: str
    state: str


class OperationView(Contract):
    id: str
    proposal_id: str
    kind: Literal['crm','email']
    effect_key: str
    payload_hash: str
    status: Literal['dispatched','unknown','verified','accepted','failed','review']
    result: Receipt | None
    recovery: Literal['reconcile_before_retry'] | None


class ReconcileResult(OperationView):
    observation: Literal['stored_only','adapter_read_back']
    adapter_available: bool


OUTPUTS={'extract_commitments':ExtractResult,'prepare_crm_update':ProposalView,
         'draft_followup':DraftResult,'reconcile_followup':ReconcileResult}
