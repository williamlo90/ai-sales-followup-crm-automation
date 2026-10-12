"""One-shot local readiness monitor with a durable alert outbox.

Invoke periodically from the chosen deployment scheduler. Delivery is at-least-once;
the local receiver should deduplicate the stable event_id/Idempotency-Key.
"""
import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

import httpx


def local_url(value):
    parsed = urlsplit(value)
    if (parsed.scheme != 'http' or parsed.hostname not in {'127.0.0.1','localhost','::1'}
            or parsed.username or parsed.password or parsed.fragment or parsed.query):
        raise ValueError('An explicit loopback HTTP URL without credentials is required')
    return value


def check(database, health_url, receiver_url, client=None):
    local_url(health_url); local_url(receiver_url)
    owned = client is None
    client = client or httpx.Client(trust_env=False,timeout=5,follow_redirects=False)
    try:
        try:
            response = client.get(health_url)
            state = 'healthy' if response.status_code == 200 else 'unavailable'
        except httpx.HTTPError:
            state = 'unavailable'
        with sqlite3.connect(database, timeout=10) as db:
            db.execute('CREATE TABLE IF NOT EXISTS health(url TEXT PRIMARY KEY,state TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS outbox(id TEXT PRIMARY KEY,body TEXT NOT NULL,delivered INTEGER NOT NULL DEFAULT 0)')
            db.execute('BEGIN IMMEDIATE')
            previous = db.execute('SELECT state FROM health WHERE url=?',(health_url,)).fetchone()
            if (previous and previous[0] != state) or (not previous and state=='unavailable'):
                ident = str(uuid4())
                event = {'event_id':ident,'type':'readiness.'+state,
                         'observed_at':datetime.now(timezone.utc).isoformat(),
                         'service':health_url}
                db.execute('INSERT INTO outbox(id,body) VALUES(?,?)',(ident,json.dumps(event)))
            db.execute('INSERT INTO health VALUES(?,?) ON CONFLICT(url) DO UPDATE SET state=excluded.state',(health_url,state))
            db.commit()
            delivered = 0
            for ident, body in db.execute('SELECT id,body FROM outbox WHERE delivered=0 ORDER BY rowid').fetchall():
                try:
                    response=client.post(receiver_url,content=body,headers={
                        'Content-Type':'application/json','Idempotency-Key':ident})
                    if not 200 <= response.status_code < 300:
                        break
                except httpx.HTTPError:
                    break
                db.execute('UPDATE outbox SET delivered=1 WHERE id=?',(ident,));db.commit()
                delivered += 1
            pending=db.execute('SELECT count(*) FROM outbox WHERE delivered=0').fetchone()[0]
            return {'readiness':state,'delivered_this_check':delivered,'pending':pending}
    finally:
        if owned:client.close()


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state',type=Path,required=True)
    parser.add_argument('--health',type=local_url,required=True)
    parser.add_argument('--receiver',type=local_url,required=True)
    args=parser.parse_args()
    print(json.dumps(check(args.state,args.health,args.receiver)))
