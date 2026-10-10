"""Persistent, fail-closed USD budget for explicit evaluation calls only.

Amounts are integer microdollars. Pending/unknown calls retain their full
reservation. The ledger never retries a call or silently raises its ceiling.
"""
import sqlite3
from contextlib import contextmanager
from pathlib import Path


class BudgetError(Exception):
    pass


def amount(value):
    if type(value) is not int or value<0:raise BudgetError('invalid_amount')
    return value


class EvaluationBudget:
    def __init__(self,path,cap_microusd=1_000_000):
        amount(cap_microusd)
        if not cap_microusd:raise BudgetError('invalid_cap')
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.transaction() as conn:
            conn.execute('CREATE TABLE IF NOT EXISTS budget(cap INTEGER NOT NULL)')
            conn.execute('CREATE TABLE IF NOT EXISTS calls(id TEXT PRIMARY KEY, metadata TEXT NOT NULL, reserved INTEGER NOT NULL, actual INTEGER, status TEXT NOT NULL)')
            row=conn.execute('SELECT cap FROM budget').fetchone()
            if row is None:conn.execute('INSERT INTO budget VALUES(?)',(cap_microusd,))
            elif row[0]!=cap_microusd:raise BudgetError('budget_cap_immutable')

    @contextmanager
    def transaction(self):
        conn=sqlite3.connect(self.path,timeout=5)
        try:
            conn.execute('BEGIN IMMEDIATE');yield conn;conn.commit()
        except Exception:
            conn.rollback();raise
        finally:conn.close()

    def reserve(self,call_id,metadata,reserved_microusd):
        amount(reserved_microusd)
        if not isinstance(call_id,str) or not call_id or not isinstance(metadata,str) or not metadata or not reserved_microusd:
            raise BudgetError('invalid_reservation')
        with self.transaction() as conn:
            if conn.execute('SELECT 1 FROM calls WHERE id=?',(call_id,)).fetchone():raise BudgetError('call_already_reserved')
            if conn.execute("SELECT 1 FROM calls WHERE status='pending'").fetchone():raise BudgetError('call_in_flight_or_interrupted')
            if conn.execute("SELECT 1 FROM calls WHERE status='overrun'").fetchone():raise BudgetError('budget_overrun_requires_review')
            used=conn.execute('SELECT coalesce(sum(max(reserved,coalesce(actual,0))),0) FROM calls').fetchone()[0]
            cap=conn.execute('SELECT cap FROM budget').fetchone()[0]
            if used+reserved_microusd>cap:raise BudgetError('budget_exhausted')
            conn.execute("INSERT INTO calls VALUES(?,?,?,NULL,'pending')",(call_id,metadata,reserved_microusd))

    def finish(self,call_id,actual_microusd=None):
        if actual_microusd is not None:amount(actual_microusd)
        with self.transaction() as conn:
            row=conn.execute('SELECT reserved,actual,status FROM calls WHERE id=?',(call_id,)).fetchone()
            if row is None:raise BudgetError('unknown_call')
            status='unknown' if actual_microusd is None else 'overrun' if actual_microusd>row[0] else 'recorded'
            if row[2]!='pending':
                if row[1]==actual_microusd and row[2]==status:return
                raise BudgetError('call_record_immutable')
            conn.execute('UPDATE calls SET actual=?,status=? WHERE id=?',(actual_microusd,status,call_id))

    def snapshot(self):
        with self.transaction() as conn:
            cap=conn.execute('SELECT cap FROM budget').fetchone()[0]
            rows=conn.execute('SELECT reserved,actual,status FROM calls').fetchall()
        committed=sum(max(r[0],r[1] or 0) for r in rows)
        return {'cap_microusd':cap,'committed_microusd':committed,'remaining_microusd':max(0,cap-committed),
                'reported_actual_microusd':sum(r[1] or 0 for r in rows),'calls':len(rows),
                'pending':sum(r[2]=='pending' for r in rows),'unknown':sum(r[2]=='unknown' for r in rows),
                'overrun':any(r[2]=='overrun' for r in rows)}
