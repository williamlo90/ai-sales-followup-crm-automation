from copy import deepcopy
from backend.evaluation_scoring import score_extraction,summarize


def example():
    source={'external_id':'thread','revision':2,'occurred_at':'2026-10-01T10:00:00Z','text':'Mia moved the call to 12:00 UTC on 2 October 2026.'}
    label={'id':'call','owner':'Mia','due_at':'2026-10-02T12:00:00Z','state':'active','revision':2,'supersedes':1,'source_id':'thread'}
    case={'id':'case','sources':[source],'expected':{'status':'ready','commitments':[label]}}
    commitment={k:v for k,v in label.items() if k!='source_id'}
    commitment.update(description='Call',observed_at=source['occurred_at'],evidence={'source_id':'thread','revision':2,'quote':source['text']})
    return case,{'status':'ready','commitments':[commitment],'missing_information':[],'conflicts':[]}


def test_correct_fields_do_not_claim_semantic_quality():
    case,raw=example();result=score_extraction(case,raw)
    assert result['automated_pass'] and result['semantic_review']=='required'
    assert summarize([case],[result])['semantic_quality_pass'] is None


def test_wrong_owner_time_revision_identity_and_extra_commitment_fail():
    case,raw=example()
    for field,value in [('owner','Other'),('due_at','2026-10-03T12:00:00Z'),('revision',3),('supersedes',None),('id','other'),('state','cancelled')]:
        changed=deepcopy(raw);changed['commitments'][0][field]=value
        assert not score_extraction(case,changed)['automated_pass'],field
    changed=deepcopy(raw);changed['commitments']*=2
    assert not score_extraction(case,changed)['automated_pass']


def test_unsupported_quote_and_stale_source_fail():
    case,raw=example()
    for key,value in [('quote','Guaranteed success'),('revision',1),('source_id','foreign')]:
        changed=deepcopy(raw);changed['commitments'][0]['evidence'][key]=value
        assert not score_extraction(case,changed)['automated_pass']


def test_provider_failure_and_missing_results_stay_in_denominator():
    case,raw=example();other={**case,'id':'missing'}
    failed=score_extraction(case,None,provider_error='timeout')
    report=summarize([case,other],[failed])
    assert report['automated_extraction']=={'correct':0,'total':2}
    assert report['missing_results']==1


def test_abstention_requires_explanation_and_no_invented_commitment():
    case,raw=example();case['expected']={'status':'review','commitments':[]}
    review={'status':'review','commitments':[],'missing_information':['owner'],'conflicts':[]}
    assert score_extraction(case,review)['automated_pass']
    review['missing_information']=[]
    assert not score_extraction(case,review)['automated_pass']
