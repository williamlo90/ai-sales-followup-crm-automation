import pytest
from backend.config import read_config, openai_profile, CANARY_MODEL
from backend.providers import ProviderError


def test_disabled_and_explicit_single_canary(tmp_path):
    path=tmp_path/'example.env'
    path.write_text('OPENAI_API_KEY=test-secret\nSALES_MODEL_ENABLED=false\nSALES_MODEL_CALL_LIMIT=1\n')
    values=read_config(path,{})
    assert openai_profile(values) is None
    profile=openai_profile(values,canary=True)
    assert profile.max_calls==1 and profile.model==CANARY_MODEL
    assert 'test-secret' not in repr(profile)


def test_no_interpolation_environment_precedence(tmp_path):
    path=tmp_path/'example.env'
    path.write_text('OPENAI_API_KEY=${FOREIGN_SECRET}\nOPENAI_MODEL=from-file\n')
    values=read_config(path,{'OPENAI_MODEL':'override','FOREIGN_SECRET':'not-authorized'})
    assert values['OPENAI_API_KEY']=='${FOREIGN_SECRET}'
    assert values['OPENAI_MODEL']=='override'
    assert 'FOREIGN_SECRET' not in values


@pytest.mark.parametrize('overrides,error',[
    ({'SALES_MODEL_ENABLED':'yes'},'invalid_model_enabled_flag'),
    ({'SALES_MODEL_CALL_LIMIT':'999'},'invalid_model_call_limit'),
    ({'OPENAI_API_KEY':''},'model_credentials_missing_or_invalid'),
    ({'OPENAI_MODEL':'secret\nvalue'},'invalid_model_name'),
    ({'OPENAI_MODEL':'expensive-unpriced-model'},'canary_requires_priced_snapshot'),
])
def test_invalid_config_fails_without_secret(overrides,error):
    values={'OPENAI_API_KEY':'secret-value','SALES_MODEL_ENABLED':'false','SALES_MODEL_CALL_LIMIT':'1'}|overrides
    with pytest.raises(ProviderError,match=error):openai_profile(values,canary=True)
