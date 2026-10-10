import json
import pytest
from scripts.postgres_app_acceptance import restart_owned_container


@pytest.mark.parametrize('wrong', ['id','label','memory'])
def test_restart_rejects_any_nonmatching_container_before_mutation(monkeypatch,wrong):
    record = {'Id':'exact-owned-id','Config':{'Labels':{'sales.phase7.owner':'pg256-acceptance'}},'HostConfig':{'Memory':268435456}}
    if wrong=='id':record['Id']='another-container'
    if wrong=='label':record['Config']['Labels']['sales.phase7.owner']='other-project'
    if wrong=='memory':record['HostConfig']['Memory']=536870912
    monkeypatch.setattr('scripts.postgres_app_acceptance.subprocess.check_output',lambda *a,**k:json.dumps([record]))
    def deny(*a,**k):pytest.fail('Restart attempted for nonmatching container')
    monkeypatch.setattr('scripts.postgres_app_acceptance.subprocess.run',deny)
    with pytest.raises(ValueError,match='exact owned'):restart_owned_container('exact-owned-id')
