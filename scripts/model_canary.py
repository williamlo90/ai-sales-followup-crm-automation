"""One explicit synthetic request; persistent reservation prevents accidental reruns."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from backend.config import ROOT, read_config, openai_profile
from backend.domain import SalesService, DomainError
from backend.store import Store
from backend.models import Actor, DealInput, SourceInput
from backend.sales_rules import Commitment
from backend.providers import ModelAdapter, ProviderError
from backend.skills import SkillService

SOURCE = 'I, Alice, will send the pricing proposal for the Northstar pilot by 2026-10-15 at 10:00 UTC.'


def exercise(adapter, directory):
    sales = SalesService(Store(str(Path(directory) / 'canary.sqlite')))
    operator = Actor(id='synthetic-operator', tenant_id='synthetic', role='operator', deal_ids={'pilot'})
    worker = operator.model_copy(update={'id':'synthetic-worker','role':'worker'})
    sales.put_deal(worker, 'pilot', DealInput(account_id='northstar', title='Northstar pilot', recipient='test@example.invalid', version=1))
    sales.put_source(worker, 'pilot', SourceInput(external_id='synthetic-message', revision=1, occurred_at='2026-10-09T00:00:00Z', text=SOURCE))
    skills = SkillService(sales, adapter)
    result = skills.invoke(operator, 'extract_commitments', {'deal_id':'pilot'})['result']
    extraction = result['extraction']
    if extraction['status'] != 'ready' or len(extraction['commitments']) != 1:
        raise DomainError('canary_expected_one_commitment')
    commitment = Commitment.model_validate(extraction['commitments'][0])
    if (commitment.owner != 'Alice' or commitment.due_at != datetime(2026,10,15,10,tzinfo=timezone.utc)
            or commitment.revision != 1 or commitment.supersedes is not None or commitment.state != 'active'
            or 'pricing' not in commitment.description.lower()):
        raise DomainError('canary_semantics_mismatch')
    sales.commitment(operator, 'pilot', commitment)
    proposal = skills.invoke(operator, 'prepare_crm_update', {'deal_id':'pilot','deal_version':1,
        'commitment':{'id':commitment.id,'revision':commitment.revision}})['result']
    draft = skills.invoke(operator, 'draft_followup', {'proposal_id':proposal['id']})['result']
    if not draft['review_required'] or draft['send_enabled'] or draft['recipient'] != 'test@example.invalid':
        raise DomainError('canary_review_boundary_failure')
    usage = result['trace']['usage']
    result['trace']['cost_usd'] = round((usage.get('input_tokens',0)*0.4 + usage.get('output_tokens',0)*1.6)/1_000_000, 8)
    result['trace']['cost_basis'] = 'estimated standard uncached token rates, USD; not billing receipt'
    return {'extraction':extraction, 'trace':result['trace'], 'checks':{
        'source_evidence':True,'owner_due_revision':True,'proposal_prepared':True,'draft_requires_review':True,
        'approval_or_external_write':False}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    values = read_config()
    if not args.run:
        print(json.dumps({'key_present':bool(values['OPENAI_API_KEY']), 'model_configured':bool(values['OPENAI_MODEL']),
                          'app_enabled':values['SALES_MODEL_ENABLED']=='true','network_called':False}))
        return 0
    try:
        profile = openai_profile(values, canary=True)
    except ProviderError as exc:
        print(json.dumps({'status':'blocked','error':str(exc)})); return 2
    target = ROOT / 'local' / 'openai-canary.json'
    target.parent.mkdir(exist_ok=True)
    record = {'status':'reserved','at':datetime.now(timezone.utc).isoformat(),'provider':'openai','model':profile.model,
              'request_limit':1,'synthetic_source_sha256':hashlib.sha256(SOURCE.encode()).hexdigest()}
    try:
        with target.open('x', encoding='utf-8') as file:
            json.dump(record,file,indent=2)
    except FileExistsError:
        print(json.dumps({'status':'blocked','error':'canary_already_reserved_or_completed'})); return 2
    try:
        with TemporaryDirectory(prefix='sales-canary-') as temporary:
            record.update(exercise(ModelAdapter(profile),temporary))
        record['status'] = 'passed'
    except (ProviderError, DomainError) as exc:
        record.update(status='failed',error=exc.code if isinstance(exc,DomainError) else str(exc))
    except Exception:
        # Never serialize exceptions that could contain transport credentials or source content.
        record.update(status='failed',error='canary_internal_error')
    target.write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(json.dumps(record,indent=2))
    return 0 if record['status']=='passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
