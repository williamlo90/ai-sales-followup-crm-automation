"""Offline dataset preflight. A passing manifest is not a quality benchmark."""
import argparse
import hashlib
import json
import re
from pathlib import Path


def audit(dev, heldout):
    issues=[];seen_ids=set();seen_text={};families={};counts={};threads={}
    for split,document in [('development-regression',dev),('held-out',heldout)]:
        if document.get('split')!=split:issues.append(f'{split}: incorrect split label')
        cases=document.get('cases',[])
        if not isinstance(cases,list):raise ValueError('cases must be a list')
        families[split]=set();threads[split]=set();counts[split]=len(cases)
        for case in cases:
            ident=case.get('id');family=case.get('account_family')
            if not isinstance(ident,str) or not ident.strip() or ident in seen_ids:issues.append(f'{split}: missing or duplicate case ID')
            seen_ids.add(ident)
            if not isinstance(family,str) or not family.strip():issues.append(f'{split}: missing account family')
            else:families[split].add(family.strip().casefold())
            if not isinstance(case.get('expected'),dict) or not case['expected']:issues.append(f'{ident}: missing expected outcomes')
            thread=case.get('thread_family')
            if isinstance(thread,str) and thread.strip():threads[split].add(thread.strip().casefold())
            messages=case.get('messages',[])
            if not isinstance(messages,list) or not all(isinstance(m,str) for m in messages):raise ValueError('messages must be strings')
            sources=case.get('sources')
            if sources is not None and (not isinstance(sources,list) or [s.get('text') for s in sources if isinstance(s,dict)]!=messages):issues.append(f'{ident}: source messages differ from model inputs')
            text=re.sub(r'\s+',' ',' '.join(messages)).strip().casefold()
            if text:
                digest=hashlib.sha256(text.encode()).hexdigest()
                if digest in seen_text and seen_text[digest]!=split:issues.append(f'{ident}: source text overlaps across splits')
                seen_text[digest]=split
            elif not all(case.get(k) for k in ['source_at','last_contact_at']):issues.append(f'{ident}: missing source input')
        if len(families[split])<20:issues.append(f'{split}: requires at least 20 account families')
    if families['development-regression'] & families['held-out']:issues.append('account families overlap across splits')
    if threads['development-regression'] & threads['held-out']:issues.append('thread families overlap across splits')
    digest=hashlib.sha256(json.dumps({'dev':dev,'heldout':heldout},sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    return {'ready_for_label_review':not issues,'case_counts':counts,'family_counts':{k:len(v) for k,v in families.items()},
            'dataset_sha256':digest,'issues':issues,'quality_evaluated':False}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('dev',type=Path);parser.add_argument('heldout',type=Path)
    args=parser.parse_args()
    report=audit(json.loads(args.dev.read_text(encoding='utf-8')),json.loads(args.heldout.read_text(encoding='utf-8')))
    print(json.dumps(report,indent=2))
    return 0 if report['ready_for_label_review'] else 2


if __name__=='__main__':raise SystemExit(main())
