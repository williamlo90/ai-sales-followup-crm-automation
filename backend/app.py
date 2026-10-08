import hashlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Annotated
from uuid import uuid4
from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from backend.domain import DomainError, SalesService
from backend.models import Actor, ApprovalInput, DealInput, ProposalInput, SourceInput, PrepareCommitmentInput
from backend.store import Store
from backend.sales_rules import Commitment
from fastapi import Query
from typing import Literal
from backend.skills import SkillService
from backend.providers import ProviderError
from pydantic import ValidationError


def create_app(service: SalesService, identities: dict[str, Actor], skills: SkillService | None=None) -> FastAPI:
    app = FastAPI(title="Sales Follow-up", version="0.1.0")
    bearer = HTTPBearer(auto_error=False)
    skill_service=skills or SkillService(service)

    def actor(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]):
        if not credentials or len(credentials.credentials) > 256:
            raise DomainError("authentication_required", 401)
        digest = hashlib.sha256(credentials.credentials.encode()).hexdigest()
        current = identities.get(digest)
        if not current:
            raise DomainError("invalid_session", 401)
        return current

    @app.middleware("http")
    async def headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = str(uuid4())
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.exception_handler(DomainError)
    async def domain_error(request, exc):
        return JSONResponse(status_code=exc.status, content={"error": exc.code},
                            headers={"WWW-Authenticate": "Bearer"} if exc.status == 401 else None)

    @app.exception_handler(RequestValidationError)
    async def invalid(request, exc):
        return JSONResponse(status_code=422, content={"error": "invalid_input"})

    @app.exception_handler(ValidationError)
    async def skill_invalid(request,exc):
        return JSONResponse(status_code=422,content={'error':'invalid_skill_input'})

    @app.exception_handler(ProviderError)
    async def provider_error(request,exc):
        return JSONResponse(status_code=503,content={'error':str(exc)})

    @app.exception_handler(sqlite3.Error)
    async def database_error(request, exc):
        return JSONResponse(status_code=503, content={"error": "local_store_unavailable"})

    @app.get("/health/live")
    def live():
        return {"status": "alive"}

    @app.get("/health/ready")
    def ready():
        with service.store.connect() as conn:
            conn.execute("SELECT 1 FROM proposals LIMIT 1")
        return {"status": "ready", "storage": "sqlite-local-harness", "connected": False, "send_enabled": False}

    @app.get("/v1/me")
    def me(current: Actor = Depends(actor)):
        return current

    @app.put("/v1/ingest/deals/{deal_id}")
    def deal(deal_id: str, data: DealInput, current: Actor = Depends(actor)):
        return service.put_deal(current, deal_id, data)

    @app.put("/v1/ingest/deals/{deal_id}/sources")
    def source(deal_id: str, data: SourceInput, current: Actor = Depends(actor)):
        return service.put_source(current, deal_id, data)

    @app.post("/v1/proposals", status_code=201)
    def prepare(data: ProposalInput, current: Actor = Depends(actor)):
        return service.prepare(current, data)

    @app.get("/v1/proposals")
    def proposals(current: Actor = Depends(actor)):
        return {"items": service.list(current)}

    @app.get("/v1/proposals/{ident}")
    def proposal(ident: str, current: Actor = Depends(actor)):
        return service.get(current, ident)

    @app.post("/v1/proposals/{ident}/approvals")
    def approve(ident: str, data: ApprovalInput, current: Actor = Depends(actor)):
        return service.approve(current, ident, data)

    @app.get("/v1/deals/match")
    def match(account_id: str = Query(min_length=1,max_length=200),
              deal_id: str | None = Query(default=None,max_length=200), current: Actor = Depends(actor)):
        return service.match(current,account_id,deal_id)

    @app.post("/v1/deals/{deal_id}/commitments")
    def commitment(deal_id: str,data: Commitment,current: Actor = Depends(actor)):
        return service.commitment(current,deal_id,data)

    @app.get("/v1/deals/{deal_id}/commitments")
    def commitments(deal_id: str,current: Actor = Depends(actor)):
        return {"items":service.commitments(current,deal_id)}

    @app.get("/v1/proposals/{ident}/eligibility")
    def eligibility(ident: str,kind: Literal["crm","email"],current: Actor = Depends(actor)):
        return service.due(current,ident,kind)

    @app.post("/v1/deals/{deal_id}/prepare-commitment",status_code=201)
    def prepare_commitment(deal_id: str,data: PrepareCommitmentInput,current: Actor = Depends(actor)):
        return service.prepare_commitment(current,deal_id,data)

    @app.get("/v1/operations/{ident}")
    def operation(ident: str,current: Actor = Depends(actor)):
        return service.operation(current,ident)

    @app.get("/v1/proposals/{ident}/operations")
    def proposal_operations(ident: str,current: Actor = Depends(actor)):
        return {"items":service.proposal_operations(current,ident)}

    @app.post('/v1/skills/{name}')
    def skill(name: str,data: dict,current: Actor=Depends(actor)):
        return skill_service.invoke(current,name,data)

    return app


def from_environment():
    """Uvicorn factory; no default credentials and no implicit production mode."""
    config_path = os.environ.get("SALES_IDENTITIES_PATH")
    if not config_path:
        raise RuntimeError("Set SALES_IDENTITIES_PATH to local identity configuration")
    records = json.loads(Path(config_path).read_text(encoding="utf-8"))
    identities = {}
    for digest, record in records.items():
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise RuntimeError("Identity keys must be SHA-256 digests")
        identities[digest] = Actor.model_validate(record)
    if not identities:
        raise RuntimeError("At least one identity is required")
    return create_app(SalesService(Store(os.environ.get("SALES_DB_PATH", "local/sales.sqlite"))), identities)
