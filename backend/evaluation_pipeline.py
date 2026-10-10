"""Exercise the real sales core in an isolated native evaluation store."""
from datetime import datetime,timezone
from backend.domain import SalesService,DomainError
from backend.models import Actor,DealInput,SourceInput,PrepareCommitmentInput
from backend.providers import Extraction
from backend.sales_rules import Commitment
from backend.store import Store


def exercise(case,raw,path):
    linkage=case['linkage'];context=case['context'];deal_id=context['deal_id']
    sales=SalesService(Store(path),clock=lambda:datetime(2026,10,1,tzinfo=timezone.utc))
    operator=Actor(id='evaluation-operator',tenant_id='evaluation',role='operator',deal_ids={d['id'] for d in linkage['candidates']})
    worker=operator.model_copy(update={'id':'evaluation-worker','role':'worker'})
    for candidate in linkage['candidates']:
        sales.put_deal(worker,candidate['id'],DealInput(account_id=candidate['account_id'],title=context['title'],
            recipient='evaluation-recipient@example.test',version=1,deleted=candidate.get('deleted',False)))
    match=sales.match(operator,linkage['account_id'],linkage['explicit_deal_id'])
    record={'case_id':case['id'],'linkage':match,'linkage_correct':match['status']==linkage['expected_status'] and match['deal_id']==linkage['expected_deal_id'],
            'proposals':[],'error':None,'abstained':False,'semantic_review':'required'}
    if match['status']!='matched':record['abstained']=True
    else:
        for history in context['commitment_history']:
            c=Commitment.model_validate(history)
            sales.put_source(worker,deal_id,SourceInput(external_id=c.evidence.source_id,revision=c.evidence.revision,occurred_at=c.observed_at,text=c.evidence.quote))
            sales.commitment(operator,deal_id,c)
        for source in case['sources']:sales.put_source(worker,deal_id,SourceInput.model_validate(source))
        try:
            extraction=Extraction.model_validate(raw)
            if extraction.status!='ready':record['abstained']=True
            else:
                for c in extraction.commitments:
                    merged=sales.commitment(operator,deal_id,c)
                    if merged['status'] not in {'applied','duplicate'}:raise DomainError('commitment_merge_rejected')
                    if c.state=='cancelled':continue
                    p=sales.prepare_commitment(operator,deal_id,PrepareCommitmentInput(commitment={'id':c.id,'revision':c.revision},deal_version=1))
                    record['proposals'].append({'id':p['id'],'payload':p['payload'],'validation_error':p['validation_error'],
                        'approval_count':len(p['approvals'])})
        except DomainError as exc:record['error']=exc.code
        except Exception:record['error']='invalid_extraction'
    with sales.store.connect() as conn:
        record['operation_count']=conn.execute('SELECT count(*) FROM operations').fetchone()[0]
        record['approval_count']=conn.execute('SELECT count(*) FROM approvals').fetchone()[0]
    record['no_unauthorized_effect']=record['operation_count']==0 and record['approval_count']==0
    return record
