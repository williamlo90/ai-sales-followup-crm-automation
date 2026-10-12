"""Select one recent, explicitly named synthetic Gmail message without reading its body."""
import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote, urlencode

from backend.config import ROOT
from backend.connector_runtime import ConnectorConfig, graph_token_reader, local_file
from backend.read_clients import BoundedReader, ReadError


def select(subject: str, session: str, *, reader=None, now=None):
    if not subject.startswith('Sales OAuth end-to-end ') or len(subject) > 120:
        raise ValueError('Explicit synthetic subject required')
    folder = local_file(session, ROOT)
    folder.mkdir(parents=True, exist_ok=True)
    selected_path = folder / 'selected-message.json'
    if selected_path.exists():
        raise ValueError('Session already selected a message')
    cfg = ConnectorConfig.model_validate(json.loads((ROOT / 'local/connectors.json').read_text(encoding='utf-8')))
    if cfg.graph is None or cfg.graph.oauth is None or cfg.graph.folder.lower() != 'inbox':
        raise ValueError('Project-owned Outlook OAuth Inbox required')
    reader = reader or BoundedReader(graph_token_reader(cfg.graph))
    base = 'https://graph.microsoft.com/v1.0/users/' + quote(cfg.graph.mailbox, safe='')
    query = urlencode({'$select': 'id,subject,from,receivedDateTime', '$top': '25',
                       '$orderby': 'receivedDateTime desc'})
    data = reader.get(base + '/mailFolders/inbox/messages?' + query,
                      {'Prefer': 'IdType="ImmutableId"'})
    items = data.get('value')
    if not isinstance(items, list) or len(items) > 25:
        raise ReadError('invalid_message_page')
    now = now or datetime.now(timezone.utc)
    matches = []
    for item in items:
        if not isinstance(item, dict) or item.get('subject') != subject:
            continue
        sender_block = item.get('from')
        sender_info = sender_block.get('emailAddress') if isinstance(sender_block, dict) else None
        sender = sender_info.get('address', '') if isinstance(sender_info, dict) else ''
        if not isinstance(sender, str) or not sender.lower().endswith('@gmail.com'):
            continue
        try:
            received = datetime.fromisoformat(item['receivedDateTime'].replace('Z', '+00:00'))
            if received.tzinfo is None or not now - timedelta(hours=24) <= received <= now:
                continue
            if not isinstance(item['id'], str) or not item['id']:
                continue
        except (KeyError, TypeError, ValueError):
            continue
        matches.append({'id': item['id'], 'subject': subject, 'received_at': received.isoformat()})
    if len(matches) != 1:
        return {'status': 'not_found' if not matches else 'ambiguous', 'matches': len(matches),
                'body_requested': False}
    with selected_path.open('x', encoding='utf-8') as handle:
        json.dump(matches[0], handle)
    return {'status': 'selected', 'matches': 1, 'body_requested': False,
            'selected_path': str(selected_path.relative_to(ROOT))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--subject', required=True)
    parser.add_argument('--session', required=True)
    args = parser.parse_args()
    try:
        result = select(args.subject, args.session)
    except (OSError, ValueError, KeyError, TypeError, ReadError) as error:
        result = {'status': 'blocked', 'reason': error.code if isinstance(error, ReadError) else type(error).__name__}
    print(json.dumps(result))
    return 0 if result['status'] == 'selected' else 1


if __name__ == '__main__':
    raise SystemExit(main())
