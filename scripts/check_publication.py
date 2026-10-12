"""Reject runtime/private paths from the Git publication tree."""
import subprocess
from pathlib import PurePosixPath


FORBIDDEN_TOP = {'local', '.venv', 'node_modules', 'dist', '__pycache__', '.pytest_cache'}
FORBIDDEN_NAMES = {'.env', 'graph-token', 'postgres_password', 'n8n_encryption_key',
                   'access-tokens.json', 'identities.json', 'connectors.json'}
FORBIDDEN_SUFFIXES = {'.sqlite', '.db', '.pem', '.key', '.pfx', '.p12', '.zip'}


def check(paths):
    bad = []
    for raw in paths:
        path = PurePosixPath(raw.replace('\\', '/'))
        parts = path.parts
        if (any(part in FORBIDDEN_TOP for part in parts)
                or path.name in FORBIDDEN_NAMES
                or (path.name.startswith('.env.') and path.name != '.env.example')
                or path.suffix.lower() in FORBIDDEN_SUFFIXES):
            bad.append(raw)
    return bad


def main():
    result = subprocess.run(['git', 'ls-files', '-z'], capture_output=True, check=True)
    files = [name.decode('utf-8') for name in result.stdout.split(b'\0') if name]
    if bad := check(files):
        raise SystemExit('Forbidden tracked paths: ' + ', '.join(sorted(bad)))
    print(f'Publication path check passed for {len(files)} tracked files')


if __name__ == '__main__':
    main()
