"""Small export/endpoint contract runner. Does not emulate or validate n8n."""
from urllib.parse import urlsplit

VERSIONS={'scheduleTrigger':1.4,'httpRequest':4.5,'if':2.3,'wait':1.1}


def validate(document):
    assert document['active'] is False
    assert document['settings']['timezone']=='Asia/Jakarta'
    assert 190<=document['settings']['executionTimeout']<=300
    nodes={n['name']:n for n in document['nodes']}
    assert len(nodes)==len(document['nodes'])==5
    assert len({n['id'] for n in nodes.values()})==5
    for n in nodes.values():
        kind=n['type'].removeprefix('n8n-nodes-base.')
        assert n['typeVersion']==VERSIONS[kind]
        if kind=='httpRequest':
            assert n['retryOnFail'] is False and n['parameters']['method']=='POST'
            assert n['parameters']['genericAuthType']=='httpHeaderAuth'
            assert n['parameters']['options']['timeout']<=65000
            assert urlsplit(n['parameters']['url']).path in {'/v1/workflows/intake/tick','/v1/workflows/due/tick'}
        if kind=='wait':assert n['parameters']=={'resume':'timeInterval','amount':60,'unit':'seconds'}
    for source,connections in document['connections'].items():
        assert source in nodes
        for branch in connections['main']:
            for edge in branch:assert edge['node'] in nodes
    return nodes


def run(document,client,token,wait):
    nodes=validate(document);name='Schedule';output={};visited=[]
    for _ in range(5):
        visited.append(name);node=nodes[name];kind=node['type'].split('.')[-1];branch=0
        if kind=='httpRequest':
            response=client.post(urlsplit(node['parameters']['url']).path,headers={'Authorization':'Bearer '+token})
            response.raise_for_status();output=response.json()
        elif kind=='if':branch=0 if output.get('needs_poll') is True else 1
        elif kind=='wait':wait(node['parameters']['amount'],output)
        links=document['connections'].get(name,{}).get('main',[])
        if not links or not links[branch]:return {'visited':visited,'result':output}
        name=links[branch][0]['node']
    raise ValueError('workflow_step_limit')
