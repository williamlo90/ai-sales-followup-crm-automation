"""Synthetic consistency checks, never evidence of human performance."""
from datetime import timedelta
import hashlib
import json
from uuid import uuid4
import pytest
from test_manual_review_scoring import fixture
from scripts.score_manual_review import stamp
from scripts.score_live_manual_review import score_live


def live_fixture(folder):
    session, raw = fixture()
    session['session_id'] = str(uuid4())
    for row in session['records']:
        row['system_wait_seconds'] = 0
        row['request_events'] = []
        row['server_receipt'] = None
        if row['mode'] == 'assisted':
            end = stamp(row['events'][0]['utc'])
            row['system_wait_seconds'] = 1
            row['request_events'] = [
                {'type': 'request', 'utc': (end-timedelta(seconds=1)).isoformat()},
                {'type': 'response', 'utc': end.isoformat()},
            ]
            receipt = dict(session_id=session['session_id'], case_id=row['case_id'],
                           dataset_sha256=session['dataset_sha256'], answer=row['initial_answer'], core_seconds=0.001)
            receipt['receipt_sha256'] = hashlib.sha256(json.dumps(receipt, sort_keys=True).encode()).hexdigest()
            row['server_receipt'] = receipt
            (folder/f"{session['session_id']}-{row['case_id']}.json").write_text(json.dumps(receipt))
    return session, raw


def test_live_waits_keep_active_time_separate(tmp_path):
    session, raw = live_fixture(tmp_path)
    result = score_live(session, raw, tmp_path)
    assert result['groups']['assisted']['system_wait_seconds'] == 4
    assert result['groups']['assisted']['active_seconds'] == 20
    assert result['groups']['manual']['system_wait_seconds'] == 0
    assert session['records'][1]['system_wait_seconds'] == 1


@pytest.mark.parametrize('tamper', ['duration', 'receipt', 'overlap', 'manual_assist', 'duplicate'])
def test_live_tampering_rejected(tmp_path, tamper):
    session, raw = live_fixture(tmp_path)
    row = session['records'][1]
    if tamper == 'duration': row['system_wait_seconds'] = 5
    if tamper == 'receipt': row['server_receipt']['core_seconds'] = 0.2
    if tamper == 'overlap': row['request_events'][1]['utc'] = session['exported_utc']
    if tamper == 'manual_assist': session['records'][0]['system_wait_seconds'] = 1
    if tamper == 'duplicate': session['records'][2] = row
    with pytest.raises(ValueError): score_live(session, raw, tmp_path)
