"""Bounded delegated Graph check; no message bodies, writes or ingestion."""
import argparse
import json
from urllib.parse import quote

from backend.config import ROOT
from backend.connector_runtime import GraphConfig, local_file, token_reader
from backend.read_clients import BoundedReader, ReadError


def check(config, *, root=ROOT, transport=None):
    cfg = GraphConfig.model_validate(config)
    token = token_reader(cfg.token_file, root)
    reader = BoundedReader(token, transport=transport)
    me = reader.get('https://graph.microsoft.com/v1.0/me?$select=id,mail,userPrincipalName')
    expected = cfg.mailbox.strip().casefold()
    identities = {v.casefold() for key in ('id', 'mail', 'userPrincipalName')
                  if isinstance((v := me.get(key)), str) and v}
    if expected not in identities:
        raise ReadError('mailbox_identity_mismatch')
    ident = me.get('id')
    if not isinstance(ident, str) or not ident:
        raise ReadError('invalid_identity')
    # Use the same /users addressing as the production adapter. No delta
    # checkpoint is advanced; personal-account aliases may require the user ID.
    path = '/v1.0/users/' + quote(cfg.mailbox, safe='')
    path += '/mailFolders/' + quote(cfg.folder, safe='') + '/messages?$top=1&$select=id'
    page = reader.get('https://graph.microsoft.com' + path, {'Prefer': 'IdType="ImmutableId"'})
    items = page.get('value')
    if (not isinstance(items, list) or len(items) > 1
            or any(not isinstance(item, dict) or not isinstance(item.get('id'), str) for item in items)):
        raise ReadError('invalid_message_page')
    return {'status': 'passed', 'identity_matches': True, 'message_ids_observed': len(items),
            'message_bodies_requested': False, 'pagination_followed': False,
            'external_writes': 0, 'scope': 'delegated profile and bounded mailbox read only'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='local/connectors.json')
    args = parser.parse_args()
    try:
        cfg = json.loads(local_file(args.config).read_text(encoding='utf-8-sig'))
        result = check(cfg['graph'])
    except ReadError as exc:
        result = {'status': 'blocked', 'reason': exc.code}
    except (OSError, ValueError, KeyError, TypeError):
        # Validation errors can contain input values. Never print them.
        result = {'status': 'blocked', 'reason': 'invalid_local_configuration'}
    print(json.dumps(result))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
