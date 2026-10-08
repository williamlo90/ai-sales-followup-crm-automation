"""Plan PostgreSQL migrations without connecting. Explicit application is Phase 7."""
import argparse
import hashlib
import json
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]/'backend/migrations'


def plan(root=ROOT):
    result=[]
    for path in sorted(root.glob('*.sql')):
        source=path.read_text(encoding='utf-8')
        result.append({'version':path.stem,'sha256':hashlib.sha256(source.encode()).hexdigest(),'path':str(path)})
    if not result:
        raise ValueError('No migrations found')
    return result


def apply(connection,root=ROOT):
    # Import/connection lifecycle is owned by the CLI. Each DDL migration and its
    # fingerprint commit atomically. An altered applied file is an explicit error.
    with connection.transaction():
        connection.execute('CREATE TABLE IF NOT EXISTS migration_checksums(version text PRIMARY KEY,sha256 char(64) NOT NULL)')
    for item in plan(root):
        with connection.transaction():
            connection.execute("SELECT pg_advisory_xact_lock(8040001)")
            old=connection.execute('SELECT sha256 FROM migration_checksums WHERE version=%s',(item['version'],)).fetchone()
            if old:
                if old[0]!=item['sha256']:
                    raise ValueError('Applied migration checksum mismatch: '+item['version'])
                continue
            source=Path(item['path']).read_text(encoding='utf-8')
            lines=[line for line in source.splitlines() if line.strip().upper() not in {'BEGIN;','COMMIT;'}]
            connection.execute('\n'.join(lines))
            connection.execute('INSERT INTO migration_checksums VALUES(%s,%s)',(item['version'],item['sha256']))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    if not args.apply:
        print(json.dumps(plan(),indent=2))
        return
    if os.environ.get('SALES_PHASE7_MIGRATIONS')!='enabled':
        raise SystemExit('Migration application is reserved for Phase 7. Default mode only plans.')
    if not os.environ.get('SALES_POSTGRES_DSN'):
        raise SystemExit('SALES_POSTGRES_DSN is required; never print its value.')
    import psycopg
    with psycopg.connect(os.environ['SALES_POSTGRES_DSN'],autocommit=True) as connection:
        apply(connection)
    print('Migrations applied; run database acceptance before declaring readiness.')


if __name__=='__main__':
    main()
