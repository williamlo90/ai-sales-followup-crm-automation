"""Generate offline human worksheet; suggestions use the real core."""
import hashlib
import json
from datetime import datetime
from backend.config import ROOT
from backend.sales_rules import due_eligibility


def prepare():
    data=(ROOT/'fixtures/evaluation/manual-review-v1.json').read_bytes();fixture=json.loads(data);tasks=[]
    for row in fixture['tasks']:
        args={k:datetime.fromisoformat(v) if k in {'due_at','now','source_at','last_contact'} and v else v for k,v in row['input'].items()}
        suggestion=due_eligibility(**args)
        if suggestion!=row['expected']:raise ValueError('Core differs from expected behavior')
        tasks.append({k:v for k,v in row.items() if k!='expected'} | {'suggestion':suggestion if row['mode']=='assisted' else None})
    pack={'hash':hashlib.sha256(data).hexdigest(),'scope':fixture['scope'],'tasks':tasks}
    target=ROOT/'local/phase-6/manual-review.html';target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text((ROOT/'scripts/manual_review.html').read_text(encoding='utf-8').replace('__PACK__',json.dumps(pack)),encoding='utf-8')
    print(target)


if __name__=='__main__':prepare()
