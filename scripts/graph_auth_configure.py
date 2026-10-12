"""Switch this project's Graph connector to Outlook OAuth without enabling sends."""
import argparse
import json
from uuid import UUID

from backend.config import ROOT
from backend.connector_runtime import ConnectorConfig, local_file


def configure(client_id: str, config='local/connectors.json', *, root=ROOT):
    UUID(client_id)
    path = local_file(config,root)
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(data.get('graph'),dict):
        raise ValueError('Graph connector missing')
    data['graph'].pop('token_file',None)
    data['graph']['oauth']={'client_id':client_id,'cache_file':'local/secrets/graph-msal-cache.bin'}
    data['email_send_enabled']=False
    ConnectorConfig.model_validate(data)
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    temporary.replace(path)
    return {'status':'configured','email_send_enabled':False,'next':'python -m scripts.graph_login'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--client-id',required=True,help='Application (client) ID from Microsoft Entra')
    parser.add_argument('--config',default='local/connectors.json')
    args=parser.parse_args()
    try:
        print(json.dumps(configure(args.client_id,args.config)))
        return 0
    except (ValueError,OSError,KeyError,TypeError):
        print(json.dumps({'status':'blocked','reason':'invalid_local_configuration_or_client_id'}))
        return 1


if __name__=='__main__':
    raise SystemExit(main())
