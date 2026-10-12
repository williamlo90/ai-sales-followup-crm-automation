"""One project-owned Outlook OAuth send through the local approval API.

Requires a fresh, ignored session/send-authorization.json containing
{"recipient": "self@example.com", "maximum_sends": 1, "sent": false}.
An attempt file is reserved before Graph is called; never rerun that session.
"""
import argparse
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.connector_runtime import ConnectorConfig, graph_token_reader, local_file
from backend.domain import SalesService
from backend.execution import ExecutionService
from backend.graph_effects import GraphMailAdapter
from backend.models import Actor
from backend.store import Store
from backend.config import ROOT


def _save_new(path: Path, value: dict):
    with path.open('x', encoding='utf-8') as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)


def run(session: str):
    folder = local_file(session, ROOT)
    if not folder.is_dir():
        raise ValueError('Session directory missing')
    permit = json.loads((folder / 'send-authorization.json').read_text(encoding='utf-8'))
    if permit.get('maximum_sends') != 1 or permit.get('sent') is not False:
        raise ValueError('One-send authorization required')
    if any((folder / name).exists() for name in ('send-attempt.json', 'send-operation.json')):
        raise ValueError('Session already attempted; observe only')
    config = ConnectorConfig.model_validate(json.loads((ROOT / 'local/connectors.json').read_text(encoding='utf-8')))
    if config.graph is None or config.graph.oauth is None:
        raise ValueError('Project-owned Outlook OAuth required')
    recipient = permit.get('recipient')
    if not isinstance(recipient, str) or not recipient:
        raise ValueError('Explicit Outlook self-test recipient required')
    prior = json.loads((ROOT / 'local/graph-ingestion/send-authorization.json').read_text(encoding='utf-8'))
    if recipient != prior.get('recipient') or not prior.get('sent'):
        raise ValueError('Recipient must match the established self-test mailbox')
    token = graph_token_reader(config.graph)
    token()  # Fail before creating an attempt if silent refresh is unavailable.

    tenant = str(uuid4())
    deal = 'oauth-mail-test'
    actor_tokens = {role: uuid4().hex for role in ('worker', 'operator', 'approver')}
    actors = {role: Actor(id=str(uuid4()), tenant_id=tenant, role=role, deal_ids={deal}) for role in actor_tokens}
    identities = {hashlib.sha256(actor_tokens[role].encode()).hexdigest(): actor for role, actor in actors.items()}
    service = SalesService(Store(folder / 'sales.sqlite'))
    adapter = GraphMailAdapter(tenant, config.graph.mailbox, token,
                               lambda t, p: service.get(actors['worker'], p)['payload'],
                               recipients=frozenset({recipient}), send_enabled=True)
    execution = ExecutionService(service, adapter, enabled=True, crm_enabled=False,
                                 send_enabled=True, recipients=frozenset({recipient}))
    app = create_app(service, identities, execution=execution)

    def request(client, role, method, path, data=None):
        response = client.request(method, path, json=data,
                                  headers={'Authorization': 'Bearer ' + actor_tokens[role]})
        if response.status_code >= 400:
            raise ValueError(f'Application API {path} returned {response.status_code}: {response.json().get("error", "unknown")}')
        return response.json()

    now = datetime.now(timezone.utc)
    body = 'Ini satu email percobaan dari AI Sales Follow-up dengan OAuth Outlook milik proyek. Tidak perlu membalas.'
    subject = '[SALES-P04] Uji OAuth approval ' + uuid4().hex[:8]
    source_id = 'oauth-user-authorized-test'
    with TestClient(app) as client:
        request(client, 'worker', 'PUT', f'/v1/ingest/deals/{deal}',
                {'account_id': 'self-test', 'title': 'Authorized Outlook OAuth email test',
                 'recipient': recipient, 'version': 1})
        request(client, 'worker', 'PUT', f'/v1/ingest/deals/{deal}/sources',
                {'external_id': source_id, 'revision': 1, 'occurred_at': now.isoformat(), 'text': body})
        proposal = request(client, 'operator', 'POST', '/v1/proposals',
                           {'deal_id': deal, 'deal_version': 1,
                            'evidence': [{'source_id': source_id, 'revision': 1, 'quote': body}],
                            'summary': subject, 'draft': body,
                            'due_at': (now - timedelta(seconds=1)).isoformat()})
        proposal_id = proposal['id']
        denied = client.post(f'/v1/proposals/{proposal_id}/execute/email',
                             headers={'Authorization': 'Bearer ' + actor_tokens['operator']})
        if denied.status_code != 403 or denied.json().get('error') != 'approval_required':
            raise ValueError('Unapproved send was not denied')
        request(client, 'approver', 'POST', f'/v1/proposals/{proposal_id}/approvals',
                {'kind': 'email', 'payload_hash': proposal['payload_hash']})
        _save_new(folder / 'send-intent.json', {'recipient': recipient, 'subject': subject,
                                               'body': body, 'proposal_id': proposal_id,
                                               'payload_hash': proposal['payload_hash']})
        _save_new(folder / 'send-attempt.json', {'reserved_at': datetime.now(timezone.utc).isoformat(),
                                                'proposal_id': proposal_id, 'maximum_attempts': 1})
        operation = request(client, 'operator', 'POST', f'/v1/proposals/{proposal_id}/execute/email')
        _save_new(folder / 'send-operation.json', operation)
        repeat = request(client, 'operator', 'POST', f'/v1/proposals/{proposal_id}/execute/email')
        if repeat['id'] != operation['id']:
            raise ValueError('Repeated request did not return the existing operation')
        sent_items = False
        try:
            observed = adapter.observe({'tenant': tenant, **operation})
            sent_items = bool(observed and observed.get('state') == 'sent')
        except Exception:
            pass  # Never resend because observation failed.
    permit['sent'] = operation['status'] == 'accepted'
    permit['attempt_reserved'] = True
    (folder / 'send-authorization.json').write_text(json.dumps(permit, indent=2), encoding='utf-8')
    return {'status': operation['status'], 'send_attempts': 1,
            'unapproved_send_denied': True, 'separate_approval': True,
            'repeat_core_same_operation': True, 'sent_items_verified': sent_items,
            'received_verified': False, 'storage': 'isolated SQLite local harness',
            'send_enabled_in_project_config': config.email_send_enabled,
            'scope': 'one synthetic email to established self-test Outlook mailbox'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    if os.environ.get('SALES_GRAPH_SEND_ACCEPTANCE') != 'enabled':
        raise SystemExit('Explicit send acceptance switch required')
    try:
        result = run(args.session)
    except Exception as error:
        result = {'status': 'stopped', 'error_type': type(error).__name__,
                  'action': 'inspect private ledger; never rerun this session after attempt reservation'}
    output = local_file(args.output, ROOT)
    _save_new(output, result)
    print(json.dumps(result))
    return 0 if result['status'] == 'accepted' else 1


if __name__ == '__main__':
    raise SystemExit(main())
