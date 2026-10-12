"""Project-scoped connectors; CRM writes and allowlisted email sends opt in."""
from dataclasses import dataclass
import json
import re
from pathlib import Path
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator
from backend.config import ROOT
from backend.bindings import BindingRepository
from backend.execution import ExecutionService
from backend.graph_effects import EffectRouter, GraphMailAdapter
from backend.graph_oauth import GraphOAuthToken
from backend.ingestion import GraphIngestion
from backend.odoo_effects import OdooActivityAdapter
from backend.read_clients import GraphReadClient, OdooReadClient


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


class DealMapping(Strict):
    opportunity_id: int = Field(gt=0, strict=True)
    assignee_id: int = Field(gt=0, strict=True)


class OdooConfig(Strict):
    base_url: str
    connector_tenant: UUID
    company_id: int = Field(gt=0, strict=True)
    token_file: str
    timezone: str = 'Asia/Jakarta'
    deals: dict[str, DealMapping]


class GraphOAuthConfig(Strict):
    client_id: UUID
    cache_file: str


class GraphConfig(Strict):
    mailbox: str = Field(min_length=1)
    folder: str = 'inbox'
    token_file: str | None = None
    oauth: GraphOAuthConfig | None = None
    message_deals: dict[str,str]

    @model_validator(mode='after')
    def one_auth_method(self):
        if (self.token_file is None) == (self.oauth is None):
            raise ValueError('Select exactly one Graph authentication method')
        return self


class ConnectorConfig(Strict):
    local_tenant: UUID
    worker_id: UUID
    crm_write_enabled: bool = Field(default=False, strict=True)
    email_send_enabled: bool = Field(default=False, strict=True)
    email_recipient_allowlist: list[str] = Field(default_factory=list, max_length=20)
    odoo: OdooConfig | None = None
    graph: GraphConfig | None = None


def local_file(name, root=ROOT):
    path = (root/Path(name)).resolve()
    if not path.is_relative_to((root/'local').resolve()):
        raise ValueError('Connector files must be inside project local directory')
    return path


def token_reader(name, root=ROOT):
    path = local_file(name,root)
    def read():
        value = path.read_text(encoding='utf-8').strip()
        if not value or any(c.isspace() for c in value):
            raise ValueError('Invalid connector token file')
        return value
    return read


def graph_token_reader(cfg: GraphConfig, root=ROOT):
    if cfg.oauth is not None:
        return GraphOAuthToken(str(cfg.oauth.client_id),local_file(cfg.oauth.cache_file,root))
    return token_reader(cfg.token_file,root)


@dataclass
class Runtime:
    execution: ExecutionService
    connector: OdooActivityAdapter | None
    ingestion: GraphIngestion | None


def compose(service, identities, name, *, root=ROOT):
    cfg = ConnectorConfig.model_validate(json.loads(local_file(name,root).read_text(encoding='utf-8')))
    if cfg.crm_write_enabled and not cfg.odoo:
        raise ValueError('CRM writes require an Odoo connector')
    if cfg.email_send_enabled and not cfg.graph:
        raise ValueError('Email sends require a Graph connector')
    recipients = cfg.email_recipient_allowlist
    if cfg.email_send_enabled and not recipients:
        raise ValueError('Email sends require an explicit recipient allowlist')
    if len(set(recipients)) != len(recipients) or any(not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', recipient) for recipient in recipients):
        raise ValueError('Invalid email recipient allowlist')
    workers = {a.id:a for a in identities.values() if a.id==str(cfg.worker_id) and a.tenant_id==str(cfg.local_tenant) and a.role=='worker'}
    if len(workers)!=1:raise ValueError('Configured connector worker identity missing')
    worker = next(iter(workers.values()))
    repository = BindingRepository(service,worker)
    crm = mail = ingestion = None
    if cfg.odoo:
        item = cfg.odoo
        if not set(item.deals)<=worker.deal_ids:raise ValueError('Odoo deal mapping exceeds worker scope')
        client = OdooReadClient(item.base_url,str(item.connector_tenant),item.company_id,token_reader(item.token_file,root))
        crm = OdooActivityAdapter(client,repository.load,{k:v.model_dump() for k,v in item.deals.items()},timezone_name=item.timezone,write_enabled=cfg.crm_write_enabled)
        crm.local_tenant = str(cfg.local_tenant)
    if cfg.graph:
        item = cfg.graph
        if not set(item.message_deals.values())<=worker.deal_ids:raise ValueError('Graph mapping exceeds worker scope')
        token = graph_token_reader(item,root)
        client = GraphReadClient(str(cfg.local_tenant),item.mailbox,token,folder=item.folder)
        ingestion = GraphIngestion(service,worker,client,item.message_deals)
        mail = GraphMailAdapter(str(cfg.local_tenant),item.mailbox,token,repository.payload,
                                recipients=frozenset(recipients),send_enabled=cfg.email_send_enabled)
    if crm is None and ingestion is None:raise ValueError('No connectors configured')
    execution = ExecutionService(service,EffectRouter(crm,mail),enabled=cfg.crm_write_enabled or cfg.email_send_enabled,
                                 crm_enabled=cfg.crm_write_enabled,send_enabled=cfg.email_send_enabled,
                                 recipients=frozenset(recipients))
    return Runtime(execution,crm,ingestion)
