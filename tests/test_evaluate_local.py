import pytest
from scripts.evaluate_local import check_metadata,MODEL,RUNTIME

DIGEST='8f68893c685c'+'a'*52

def test_local_metadata_requires_full_pin_and_supported_mode():
    version={'version':RUNTIME};tags={'models':[{'name':MODEL,'digest':DIGEST}]};show={'thinking':{'values':[True,False]}}
    check_metadata(version,tags,show,DIGEST)
    for v,t,s,d in [({'version':'wrong'},tags,show,DIGEST),(version,{'models':[]},show,DIGEST),(version,tags,{},DIGEST),(version,tags,show,'short')]:
        with pytest.raises(ValueError):check_metadata(v,t,s,d)
