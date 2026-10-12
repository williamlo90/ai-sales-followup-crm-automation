"""Check only Inbox/Junk message headers for a prior self-test send."""
import argparse
import json
from urllib.parse import quote, urlencode

from backend.config import ROOT
from backend.connector_runtime import ConnectorConfig, graph_token_reader, local_file
from backend.read_clients import BoundedReader, ReadError


def check(session: str):
    folder = local_file(session, ROOT)
    intent = json.loads((folder / 'send-intent.json').read_text(encoding='utf-8'))
    cfg = ConnectorConfig.model_validate(json.loads((ROOT / 'local/connectors.json').read_text(encoding='utf-8')))
    if not cfg.graph or not cfg.graph.oauth:
        raise ValueError('Project-owned Outlook OAuth required')
    reader = BoundedReader(graph_token_reader(cfg.graph))
    base = 'https://graph.microsoft.com/v1.0/users/' + quote(cfg.graph.mailbox, safe='')
    params = urlencode({'$select': 'id,subject,receivedDateTime', '$top': '25',
                        '$orderby': 'receivedDateTime desc'})
    observed = []
    for folder_name in ('inbox', 'junkemail'):
        data = reader.get(f'{base}/mailFolders/{folder_name}/messages?{params}')
        items = data.get('value')
        if not isinstance(items, list) or len(items) > 25:
            raise ReadError('mail_observation_invalid')
        observed.extend({'folder': folder_name, 'received_at': item.get('receivedDateTime')}
                        for item in items if isinstance(item, dict) and item.get('subject') == intent['subject'])
    return {'status': 'received' if observed else 'not_observed_in_recent_inbox_or_junk',
            'matches': observed, 'message_bodies_requested': False, 'external_writes': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True)
    args = parser.parse_args()
    try:
        result = check(args.session)
    except (OSError, ValueError, KeyError, TypeError, ReadError) as error:
        result = {'status': 'blocked', 'reason': error.code if isinstance(error, ReadError) else type(error).__name__}
    print(json.dumps(result))
    return 0 if result['status'] == 'received' else 1


if __name__ == '__main__':
    raise SystemExit(main())
