from contextlib import contextmanager
from pathlib import Path
import pytest
from scripts.migrations import apply, plan


class ConnectionDouble:
    def __init__(self):self.applied={};self.calls=[];self.rollbacks=0;self.fail=False
    @contextmanager
    def transaction(self):
        snapshot=dict(self.applied)
        try:yield
        except Exception:
            self.applied=snapshot
            self.rollbacks+=1
            raise
    def execute(self,sql,params=()):
        self.calls.append(sql)
        if sql.startswith('SELECT sha256'):
            value=self.applied.get(params[0])
            self.row=(value,) if value else None
        if sql.startswith('INSERT INTO migration_checksums'):
            if self.fail:raise RuntimeError('simulated persistence failure')
            self.applied[params[0]]=params[1]
        return self
    def fetchone(self):return self.row


def test_plan_is_deterministic_and_lists_only_sql():
    assert plan()==plan()
    assert [p['version'] for p in plan()]==['001_foundation','002_sales_rules','003_model_runs']
    assert all(len(p['sha256'])==64 for p in plan())


def test_runner_replay_and_checksum_guard(tmp_path):
    file=tmp_path/'001_test.sql'
    file.write_text('BEGIN;\nCREATE TABLE demo(id int);\nCOMMIT;')
    connection=ConnectionDouble()
    apply(connection,tmp_path)
    apply(connection,tmp_path)
    assert sum('CREATE TABLE demo' in call for call in connection.calls)==1
    file.write_text('BEGIN;\nCREATE TABLE changed(id int);\nCOMMIT;')
    with pytest.raises(ValueError,match='checksum mismatch'):apply(connection,tmp_path)


def test_runner_failure_rolls_back_checksum(tmp_path):
    (tmp_path/'001_test.sql').write_text('BEGIN;\nCREATE TABLE demo(id int);\nCOMMIT;')
    connection=ConnectionDouble();connection.fail=True
    with pytest.raises(RuntimeError):apply(connection,tmp_path)
    assert connection.applied=={}
    assert connection.rollbacks==1
