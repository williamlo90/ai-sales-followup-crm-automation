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
from backend.postgres_store import PostgresStore, StorageError
from backend.sales_rules import Commitment
from fastapi import Query
from typing import Literal
from backend.skills import SkillService
from backend.providers import ProviderError
from pydantic import ValidationError, BaseModel, ConfigDict, Field
from backend.bindings import BindingRepository, ConnectorBindingInput
from backend.read_clients import ReadError
from backend.workflows import WorkflowService, EnqueueInput, RecoveryInput


class SelectedGraphMessage(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str = Field(min_length=1, max_length=4096)


def create_app(service: SalesService, identities: dict[str, Actor], skills: SkillService | None=None, execution=None, connector=None, ingestion=None) -> FastAPI:
    app = FastAPI(title="Sales Follow-up", version="0.1.0")
    bearer = HTTPBearer(auto_error=False)
    skill_service=skills or SkillService(service,execution=execution)
    workflows=WorkflowService(service,skill_service,execution)

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

    @app.exception_handler(ReadError)
    async def connector_error(request,exc):
        return JSONResponse(status_code=503,content={'error':exc.code})

    @app.exception_handler(sqlite3.Error)
    @app.exception_handler(StorageError)
    async def database_error(request, exc):
        return JSONResponse(status_code=503, content={"error": "local_store_unavailable"})

    @app.get("/health/live")
    def live():
        return {"status": "alive"}

    @app.get("/health/ready")
    def ready():
        send_enabled = bool(execution and execution.send_enabled)
        connectors_configured = {"odoo": connector is not None, "graph": ingestion is not None}
        if isinstance(service.store, PostgresStore):
            service.store.ready()
            return {"status":"ready", "storage":"postgresql", "connectors_configured":connectors_configured, "send_enabled":send_enabled}
        with service.store.connect() as conn:
            conn.execute("SELECT 1 FROM proposals LIMIT 1")
        return {"status": "ready", "storage": "sqlite-local-harness", "connectors_configured": connectors_configured, "send_enabled": send_enabled}

    @app.get("/v1/me")
    def me(current: Actor = Depends(actor)):
        return current

    @app.put("/v1/ingest/deals/{deal_id}")
    def deal(deal_id: str, data: DealInput, current: Actor = Depends(actor)):
        return service.put_deal(current, deal_id, data)

    @app.post('/v1/ingest/graph/poll')
    def graph_poll(current: Actor = Depends(actor)):
        if current.role!='worker':raise DomainError('role_not_permitted',403)
        if ingestion is None:raise DomainError('graph_not_configured',503)
        if current.id!=ingestion.actor.id or current.tenant_id!=ingestion.actor.tenant_id:
            raise DomainError('record_not_found',404)
        return ingestion.poll()  # One bounded page; caller coordinates pagination.

    @app.post('/v1/ingest/graph/selected')
    def graph_selected(data: SelectedGraphMessage,current: Actor=Depends(actor)):
        if current.role!='worker':raise DomainError('role_not_permitted',403)
        if ingestion is None:raise DomainError('graph_not_configured',503)
        if current.id!=ingestion.actor.id or current.tenant_id!=ingestion.actor.tenant_id:
            raise DomainError('record_not_found',404)
        return ingestion.selected(data.id)

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

    @app.get('/v1/deals/{deal_id}/context')
    def context(deal_id: str,current: Actor=Depends(actor)):
        return service.context(current,deal_id)

    @app.post('/v1/proposals/{ident}/execute/{kind}')
    def execute(ident: str,kind: Literal['crm','email'],current: Actor=Depends(actor)):
        service.get(current,ident)
        if execution is None:raise DomainError('execution_disabled',403)
        operation=execution.execute(current,ident,kind)
        return service.operation(current,operation['id'])

    @app.get('/v1/proposals/{ident}/connector-preparation')
    def connector_preparation(ident: str,current: Actor=Depends(actor)):
        service.get(current,ident)
        if connector is None:raise DomainError('connector_not_configured',503)
        if getattr(connector,'local_tenant',current.tenant_id)!=current.tenant_id:raise DomainError('record_not_found',404)
        return BindingRepository(service,current).preparation(ident,connector)

    @app.get('/v1/proposals/{ident}/connector-binding')
    def binding_get(ident: str,current: Actor=Depends(actor)):
        return BindingRepository(service,current).load(current.tenant_id,ident)

    @app.post('/v1/workflows/jobs',status_code=201)
    def enqueue(data: EnqueueInput,current: Actor=Depends(actor)):
        return workflows.enqueue(current,data)

    @app.post('/v1/proposals/{ident}/handoff/{kind}',status_code=201)
    def handoff(ident: str,kind: Literal['crm','email'],current: Actor=Depends(actor)):
        proposal=service.get(current,ident)
        workers={a.id:a for a in identities.values() if a.role=='worker' and a.tenant_id==current.tenant_id
                 and proposal['payload']['deal_id'] in a.deal_ids}
        if len(workers)!=1:raise DomainError('workflow_worker_configuration_required',503)
        return workflows.handoff(current,ident,next(iter(workers.values())),kind)

    @app.get('/v1/workflows/jobs')
    def workflow_list(current: Actor=Depends(actor)):
        return {'items':workflows.list(current)}

    @app.post('/v1/workflows/jobs/{ident}/recover')
    def workflow_recover(ident: str,data: RecoveryInput,current: Actor=Depends(actor)):
        return workflows.recover(current,ident,data.action)

    @app.get('/v1/workflows/jobs/{ident}')
    def workflow_get(ident: str,current: Actor=Depends(actor)):
        return workflows.get(current,ident)

    @app.post('/v1/workflows/{journey}/tick')
    def workflow_tick(journey: Literal['intake','due'],current: Actor=Depends(actor)):
        return workflows.tick(current,journey)

    @app.post('/v1/proposals/{ident}/connector-binding')
    def binding_attach(ident: str,data: ConnectorBindingInput,current: Actor=Depends(actor)):
        service.get(current,ident)
        if connector is None:raise DomainError('connector_not_configured',503)
        if getattr(connector,'local_tenant',current.tenant_id)!=current.tenant_id:raise DomainError('record_not_found',404)
        return BindingRepository(service,current).attach(ident,data,connector)

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
    from backend.config import read_config, openai_profile
    from backend.providers import ModelAdapter
    storage = os.environ.get('SALES_STORAGE', 'sqlite')
    if storage == 'postgresql':
        dsn = os.environ.get('SALES_POSTGRES_DSN')
        if not dsn: raise RuntimeError('SALES_POSTGRES_DSN required')
        store = PostgresStore(dsn)
    elif storage == 'sqlite':
        store = Store(os.environ.get('SALES_DB_PATH', 'local/sales.sqlite'))
    else: raise RuntimeError('Unsupported SALES_STORAGE')
    service = SalesService(store)
    profile = openai_profile(read_config())
    model = ModelAdapter(profile) if profile else None
    budget_path = os.environ.get('SALES_MODEL_BUDGET_PATH')
    if model and budget_path:
        from backend.connector_runtime import local_file
        from backend.evaluation_budget import EvaluationBudget
        from backend.budgeted_model import BudgetedModel
        model = BudgetedModel(model,EvaluationBudget(local_file(budget_path)))
    path = os.environ.get('SALES_CONNECTORS_PATH')
    if path:
        from backend.connector_runtime import compose
        runtime = compose(service,identities,path)
        skills = SkillService(service,model,execution=runtime.execution)
        return create_app(service,identities,skills,execution=runtime.execution,connector=runtime.connector,ingestion=runtime.ingestion)
    return create_app(service, identities, SkillService(service, model))
