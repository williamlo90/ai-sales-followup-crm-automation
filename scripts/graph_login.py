"""One-time Outlook device login; stores only an encrypted project-local token cache."""
import argparse
import json

from backend.config import ROOT
from backend.connector_runtime import GraphConfig, graph_token_reader, local_file
from backend.graph_oauth import GRAPH_SCOPES, GraphOAuthToken
from backend.read_clients import ReadError
from scripts.graph_readiness import check


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='local/connectors.json')
    args = parser.parse_args()
    try:
        raw = json.loads(local_file(args.config,ROOT).read_text(encoding='utf-8-sig'))
        cfg = GraphConfig.model_validate(raw['graph'])
        token = graph_token_reader(cfg,ROOT)
        if not isinstance(token,GraphOAuthToken):
            print('Graph OAuth is not selected in this project configuration.')
            return 1
        app = token.application(for_login=True)
        flow = app.initiate_device_flow(scopes=GRAPH_SCOPES)
        if not isinstance(flow,dict) or 'user_code' not in flow:
            print('Could not start Outlook device login.')
            return 1
        print(flow['message'],flush=True)
        result = app.acquire_token_by_device_flow(flow)
        if not isinstance(result,dict) or not result.get('access_token'):
            print('Outlook login was not completed; rerun this command when ready.')
            return 1
        # Confirm the signed-in mailbox and bounded read without a write.
        outcome = check(raw['graph'])
        print(json.dumps({'status':'connected','identity_matches':outcome['identity_matches'],
                          'message_ids_observed':outcome['message_ids_observed'],
                          'send_enabled':bool(raw.get('email_send_enabled',False))}))
        return 0
    except ReadError as exc:
        print(json.dumps({'status':'blocked','reason':exc.code}))
    except (OSError,ValueError,KeyError,TypeError):
        print(json.dumps({'status':'blocked','reason':'invalid_local_configuration'}))
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
