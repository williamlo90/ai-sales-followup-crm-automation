"""Build a deterministic, secret-free local delivery archive from explicit paths."""
import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOP = (
    '.env.example', 'README.md', 'LICENSE', 'PHASES.md', 'PROJECT-DELIVERY.md',
    'pyproject.toml', 'AI-AGENTS.md', 'REUSABLE-SKILLS.md',
    'MCP-INTEGRATIONS.md', 'N8N-AUTOMATION.md', 'BUSINESS-PLATFORM.md',
    'LOCAL-AI-AND-PROVIDERS.md', 'SECURITY-TESTING-MONITORING.md',
)
DIRS = ('backend', 'scripts', 'skills', 'automation/n8n', 'deploy',
        'fixtures', 'tests', 'web', 'mcp-server')
DOCS = ('docs/CASE-STUDY.md', 'docs/phase-7/COMPLETION-AUDIT.md',
        'docs/phase-7/CONNECTOR-SETUP.md', 'docs/phase-7/ODOO-SANDBOX-REPRO.md', 'docs/phase-7/POSTGRES-RUNTIME.md',
        'docs/phase-7/READINESS-ALERTS.md',
        'docs/phase-6/openai-profile-freeze.json', 'docs/phase-6/dataset-freeze.json',
        'docs/phase-8/OPERATOR-GUIDE.md', 'docs/phase-8/DEMO.md',
        'docs/phase-8/DELIVERY-AUDIT.md', 'docs/phase-9/DECISION.md')
IGNORED_DIRS = {'node_modules', 'dist', 'build', '__pycache__', '.pytest_cache',
                '.venv', '.git', 'playwright-report', 'test-results'}
IGNORED_SUFFIXES = {'.pyc', '.pyo', '.log', '.sqlite', '.db', '.zip', '.key', '.pem'}


def source_paths():
    candidates = [ROOT / name for name in TOP + DOCS]
    candidates.extend((ROOT / 'docs/evidence').glob('phase-7-*'))
    for dirname in DIRS:
        candidates.extend((ROOT / dirname).rglob('*'))
    files = []
    for path in candidates:
        if not path.is_file() or path.is_symlink():
            continue
        rel = path.relative_to(ROOT)
        if any(part in IGNORED_DIRS or part.startswith('.') for part in rel.parts[:-1]):
            continue
        if rel.suffix.lower() in IGNORED_SUFFIXES:
            continue
        name = rel.name.lower()
        if name.startswith('.env') and name != '.env.example':
            continue
        if any(word in name for word in ('secret', 'token', 'credential', 'password')):
            # Source code may discuss tokens; data/configuration must be examples only.
            if rel.suffix.lower() not in {'.py', '.ts', '.tsx', '.mjs', '.md'} and not name.endswith('.example.json'):
                continue
        files.append(rel)
    return sorted(set(files), key=lambda item: item.as_posix())


def git_head():
    result = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT,
                            text=True, capture_output=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def build(output):
    output = Path(output).resolve()
    if ROOT in output.parents or output == ROOT:
        if 'local' not in output.relative_to(ROOT).parts:
            raise ValueError('Release archive must be saved under local/ or outside the repository')
    output.parent.mkdir(parents=True, exist_ok=True)
    paths = source_paths()
    required = {'backend/app.py', 'backend/budgeted_model.py',
                'backend/requirements.lock', 'backend/requirements-postgres.txt',
                'automation/n8n/intake-v1.json', 'automation/n8n/due-v1.json',
                'web/package-lock.json', 'mcp-server/package-lock.json',
                'deploy/compose.yaml'}
    required.update({'docs/phase-6/openai-profile-freeze.json',
                     'docs/phase-6/dataset-freeze.json',
                     'docs/phase-8/OPERATOR-GUIDE.md', 'docs/phase-8/DEMO.md',
                     'docs/phase-8/DELIVERY-AUDIT.md', 'LICENSE',
                     'docs/phase-7/ODOO-SANDBOX-REPRO.md'})
    present = {path.as_posix() for path in paths}
    if missing := required - present:
        raise RuntimeError('Missing release inputs: ' + ', '.join(sorted(missing)))
    manifest = {
        'release': 'sales-followup-local-v1-candidate',
        'source_git_head': git_head(),
        'source_worktree': ('clean' if not subprocess.run(
            ['git', 'status', '--porcelain'], cwd=ROOT, text=True,
            capture_output=True, check=False).stdout.strip()
            else 'snapshot_includes_current_uncommitted_files'),
        'scope': 'Source, example configuration and synthetic fixtures; no secrets or local state',
        'files': {path.as_posix(): hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
                  for path in paths},
    }
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as archive:
        for path in paths:
            item = zipfile.ZipInfo(path.as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
            item.compress_type = zipfile.ZIP_DEFLATED
            item.external_attr = 0o644 << 16
            archive.writestr(item, (ROOT / path).read_bytes(), compress_type=zipfile.ZIP_DEFLATED)
        item = zipfile.ZipInfo('release-manifest.json', date_time=(1980, 1, 1, 0, 0, 0))
        item.compress_type = zipfile.ZIP_DEFLATED
        item.external_attr = 0o644 << 16
        archive.writestr(item, json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    return {'status': 'created', 'path': str(output), 'files': len(paths),
            'bytes': output.stat().st_size,
            'sha256': hashlib.sha256(output.read_bytes()).hexdigest()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default=str(ROOT / 'local/releases/sales-followup-local-v1.zip'))
    print(json.dumps(build(parser.parse_args().output), indent=2))
