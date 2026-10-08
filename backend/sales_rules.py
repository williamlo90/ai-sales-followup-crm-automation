"""Deterministic sales rules; extraction supplies candidates, never authority."""
from datetime import datetime
from typing import Literal
from pydantic import AwareDatetime, Field
from backend.models import Contract, Evidence


class Commitment(Contract):
    id: str = Field(min_length=1, max_length=200)
    revision: int = Field(ge=1)
    supersedes: int | None = Field(default=None, ge=1)
    owner: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=500)
    due_at: AwareDatetime
    observed_at: AwareDatetime
    evidence: Evidence
    state: Literal["active", "cancelled"] = "active"


def match_deal(candidates: list[dict], account_id: str, explicit_deal_id: str | None = None):
    """Caller supplies only server-scoped records; names alone never establish identity."""
    eligible = [d for d in candidates if d["account_id"] == account_id and not d.get("deleted", False)]
    if explicit_deal_id is not None:
        eligible = [d for d in eligible if d["id"] == explicit_deal_id]
    if len(eligible) == 1:
        return {"status":"matched", "deal_id":eligible[0]["id"], "reason":"explicit_deal_and_account" if explicit_deal_id else "unique_account_deal"}
    return {"status":"review", "deal_id":None, "reason":"ambiguous_deal" if len(eligible)>1 else "no_permitted_match"}


def merge_commitment(history: list[Commitment], incoming: Commitment):
    """Keep revision provenance, refuse implicit/competing changes, ignore old delivery."""
    relevant = [c for c in history if c.id == incoming.id]
    if not relevant:
        if incoming.revision != 1 or incoming.supersedes is not None:
            return {"status":"conflict", "reason":"missing_predecessor", "current":None}
        return {"status":"applied", "reason":"initial", "current":incoming}
    current = max(relevant, key=lambda c:c.revision)
    for previous in relevant:
        if previous.revision == incoming.revision:
            if previous == incoming:
                return {"status":"duplicate", "reason":"same_revision", "current":current}
            return {"status":"conflict", "reason":"competing_revision", "current":current}
    if incoming.revision < current.revision:
        return {"status":"ignored", "reason":"out_of_order", "current":current}
    if incoming.supersedes != current.revision or incoming.revision != current.revision + 1:
        return {"status":"conflict", "reason":"missing_predecessor", "current":current}
    if incoming.observed_at < current.observed_at:
        return {"status":"conflict", "reason":"chronology_conflict", "current":current}
    return {"status":"applied", "reason":"explicit_revision", "current":incoming}


def due_eligibility(due_at: datetime, now: datetime, opted_out: bool, last_contact: datetime | None,
                    source_at: datetime, approved: bool, fresh: bool):
    for reason, blocked in [("not_due", due_at>now), ("opted_out", opted_out),
                             ("already_contacted", last_contact is not None and last_contact>=source_at),
                             ("stale", not fresh), ("approval_required", not approved)]:
        if blocked:
            return {"eligible":False, "reason":reason}
    return {"eligible":True, "reason":"due_and_approved"}
