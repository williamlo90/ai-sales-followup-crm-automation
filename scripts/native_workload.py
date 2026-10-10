"""Declared 100-operation native core workload; no model, engine or network."""
import json
import math
import platform
import statistics
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import datetime,timezone
from backend.domain import SalesService
from backend.models import Actor,DealInput,SourceInput,ProposalInput
from backend.store import Store


def run():
    samples=[];counts={};errors=0
    with TemporaryDirectory(prefix='sales-native-workload-') as folder:
        service=SalesService(Store(Path(folder)/'workload.sqlite'))
        operator=Actor(id='operator',tenant_id='load',role='operator',deal_ids={'deal'})
        worker=operator.model_copy(update={'id':'worker','role':'worker'})
        service.put_deal(worker,'deal',DealInput(account_id='account',title='Native test',recipient='lab@example.test',version=1))
        service.put_source(worker,'deal',SourceInput(external_id='source',revision=1,occurred_at='2026-10-01T00:00:00Z',text='Mira will send the quote on 2026-11-02 at 09:00 UTC.'))
        for i in range(20):
            data=ProposalInput(deal_id='deal',deal_version=1,evidence=[{'source_id':'source','revision':1,'quote':'Mira will send the quote on 2026-11-02 at 09:00 UTC.'}],
                summary=f'Review quote {i}',due_at='2026-11-02T09:00:00Z',draft='Please confirm the quoted next step.')
            proposal=None
            for name in ['prepare','get','context','match','due']:
                start=time.perf_counter()
                try:
                    if name=='prepare':proposal=service.prepare(operator,data)
                    elif name=='get':service.get(operator,proposal['id'])
                    elif name=='context':service.context(operator,'deal')
                    elif name=='match':service.match(operator,'account','deal')
                    else:service.due(operator,proposal['id'],'email')
                except Exception:errors+=1
                samples.append((time.perf_counter()-start)*1000);counts[name]=counts.get(name,0)+1
    ordered=sorted(samples)
    return {'observed_at':datetime.now(timezone.utc).isoformat(),'environment':'native Python / temporary SQLite / concurrency 1',
        'python':platform.python_version(),'os':platform.platform(),'processor':platform.processor(),
        'operations':len(samples),'mix':counts,'errors':errors,'p50_ms':round(statistics.median(samples),3),
        'p90_ms':round(ordered[math.ceil(.9*len(samples))-1],3),'p95_ms':round(ordered[math.ceil(.95*len(samples))-1],3),
        'max_ms':round(max(samples),3),'target_p95_ms':500,'target_met':errors==0 and ordered[94]<=500,
        'exclusions':['setup','HTTP transport','model inference','PostgreSQL','n8n','Graph','Odoo','UI','external effects'],
        'samples_ms':samples}


if __name__=='__main__':
    record=run();directory=Path('local/phase-6');directory.mkdir(parents=True,exist_ok=True)
    target=directory/f'native-workload-{time.time_ns()}.json'
    target.write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in record.items() if k!='samples_ms'},indent=2))
