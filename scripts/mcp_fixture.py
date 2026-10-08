"""Native protocol-test backend; synthetic records and model double only."""
import hashlib
import json
import socket
import tempfile
from pathlib import Path
import httpx
import uvicorn
from backend.app import create_app
from backend.domain import SalesService
from backend.models import Actor, DealInput, SourceInput
from backend.sales_rules import Commitment
from backend.store import Store
from backend.skills import SkillService
from backend.providers import ModelAdapter, ModelProfile


if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix='sales-mcp-') as directory:
        sales=SalesService(Store(Path(directory)/'test.sqlite'))
        actors={r:Actor(id=r,tenant_id='mcp-test',role=r,deal_ids={'pilot'}) for r in ['worker','operator','approver','auditor']}
        actors['foreign']=Actor(id='foreign',tenant_id='other',role='operator',deal_ids={'pilot'})
        sales.put_deal(actors['worker'],'pilot',DealInput(account_id='northstar',title='Synthetic pilot',recipient='test@example.invalid',version=1))
        text='Alice will send pricing by 2026-10-15 10:00 UTC.'
        sales.put_source(actors['worker'],'pilot',SourceInput(external_id='message',revision=1,occurred_at='2026-10-09T00:00:00Z',text=text))
        commitment=Commitment(id='c1',revision=1,owner='Alice',description='Send pricing',due_at='2026-10-15T10:00:00Z',
            observed_at='2026-10-09T00:00:00Z',evidence={'source_id':'message','revision':1,'quote':text})
        sales.commitment(actors['operator'],'pilot',commitment)
        result={'status':'ready','commitments':[commitment.model_dump(mode='json')],'missing_information':[],'conflicts':[]}
        model=ModelAdapter(ModelProfile('ollama','contract-only',local_only=True,max_calls=1),transport=httpx.MockTransport(
            lambda request:httpx.Response(200,json={'done':True,'message':{'content':json.dumps(result)}})))
        identities={hashlib.sha256(('test-'+name).encode()).hexdigest():actor for name,actor in actors.items()}
        app=create_app(sales,identities,SkillService(sales,model))
        with socket.socket() as listener:
            listener.bind(('127.0.0.1',0));listener.listen(128)
            print(json.dumps({'port':listener.getsockname()[1]}),flush=True)
            uvicorn.Server(uvicorn.Config(app,log_level='error',access_log=False)).run(sockets=[listener])
