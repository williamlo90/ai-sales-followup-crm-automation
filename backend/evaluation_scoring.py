"""Deterministic extraction checks, separate from human semantic review."""
from datetime import datetime
from backend.providers import Extraction


def instant(value):
    return datetime.fromisoformat(value.replace('Z','+00:00'))


def score_extraction(case, raw, *, provider_error=None):
    expected=case['expected'];checks={};reasons=[]
    try:
        if provider_error:raise ValueError('provider failed')
        result=Extraction.model_validate(raw)
    except Exception:
        return {'case_id':case['id'],'automated_pass':False,'checks':{'valid_response':False},
                'failure_reasons':['provider_error' if provider_error else 'invalid_response'],
                'semantic_review':'not_scored','provider_error':provider_error}
    checks['valid_response']=True
    checks['status']=result.status==expected['status']
    labels=expected['commitments']
    checks['commitment_count']=len(result.commitments)==len(labels)
    sources={s['external_id']:s for s in case['sources']}
    checks['source_grounding']=all(
        c.evidence.source_id in sources
        and c.evidence.revision==sources[c.evidence.source_id]['revision']
        and bool(c.evidence.quote.strip())
        and c.evidence.quote in sources[c.evidence.source_id]['text']
        and c.observed_at==instant(sources[c.evidence.source_id]['occurred_at'])
        for c in result.commitments)
    # Match all labels without accepting extra/missing commitments. New IDs may
    # be model-generated; existing revision identities must be preserved.
    remaining=list(result.commitments)
    matched=True
    for label in labels:
        candidate=next((c for c in remaining if
            c.owner==label['owner'] and c.due_at==instant(label['due_at'])
            and c.state==label['state'] and c.revision==label['revision']
            and c.supersedes==label['supersedes']
            and (label.get('id') is None or c.id==label['id'])
            and c.evidence.source_id==label['source_id']),None)
        if candidate is None:matched=False
        else:remaining.remove(candidate)
    checks['commitment_fields']=matched and not remaining
    checks['review_explained']=result.status!='review' or bool(result.missing_information or result.conflicts)
    for name,passed in checks.items():
        if not passed:reasons.append(name)
    return {'case_id':case['id'],'automated_pass':all(checks.values()),'checks':checks,
            'failure_reasons':reasons,'semantic_review':'required','provider_error':None}


def summarize(cases,records):
    expected_ids={c['id'] for c in cases}
    if len(expected_ids)!=len(cases):raise ValueError('duplicate dataset case')
    by_id={r['case_id']:r for r in records}
    if len(by_id)!=len(records) or set(by_id)-expected_ids:raise ValueError('duplicate or foreign result')
    passed=sum(by_id.get(c['id'],{}).get('automated_pass') is True for c in cases)
    missing=sum(c['id'] not in by_id for c in cases)
    review=[c for c in cases if c['expected']['status']=='review']
    return {'automated_extraction':{'correct':passed,'total':len(cases)},
            'review_cases':{'correct':sum(by_id.get(c['id'],{}).get('automated_pass') is True for c in review),'total':len(review)},
            'missing_results':missing,'semantic_quality_pass':None,
            'note':'Missing/provider-error cases remain in denominator; factuality and proposal quality require separate evidence.'}
