from copy import deepcopy
from scripts.evaluation_dataset import audit


def datasets():
    return tuple({'split':split,'cases':[{'id':f'{prefix}-{i}','account_family':f'{prefix}-{i}',
        'messages':[f'{prefix} source {i}'],'expected':{'status':'review'}} for i in range(20)]}
        for prefix,split in [('dev','development-regression'),('hold','held-out')])


def test_preflight_is_not_a_quality_claim():
    dev,held=datasets();result=audit(dev,held)
    assert result['ready_for_label_review'] and not result['quality_evaluated']
    assert result['dataset_sha256']==audit(deepcopy(dev),deepcopy(held))['dataset_sha256']
    held['cases'][0]['expected']['status']='ready'
    assert audit(dev,held)['dataset_sha256']!=result['dataset_sha256']


def test_rejects_family_leakage_even_with_different_case_ids():
    dev,held=datasets();held['cases'][0]['account_family']=' DEV-0 '
    assert 'account families overlap across splits' in audit(dev,held)['issues']


def test_rejects_source_leakage_with_renamed_families():
    dev,held=datasets();held['cases'][0]['messages']=['  DEV source 0  ']
    assert any('source text overlaps' in i for i in audit(dev,held)['issues'])


def test_rejects_insufficient_families_missing_labels_and_duplicate_ids():
    dev,held=datasets();held['cases']=held['cases'][:1];held['cases'][0]['id']='dev-0';held['cases'][0]['expected']={}
    result=audit(dev,held)
    assert not result['ready_for_label_review']
    assert any('missing expected' in i for i in result['issues'])
    assert any('duplicate' in i for i in result['issues'])
    assert any('20 account families' in i for i in result['issues'])
