import json
import zipfile

import pytest

from scripts.package_release import build
from scripts.verify_release import verify


def test_archive_is_deterministic_and_manifest_complete(tmp_path):
    first, second = tmp_path / 'one.zip', tmp_path / 'two.zip'
    result = build(first)
    build(second)
    assert first.read_bytes() == second.read_bytes()
    assert verify(first)['archive_sha256'] == result['sha256']
    with zipfile.ZipFile(first) as archive:
        names = set(archive.namelist())
        assert {'docs/phase-6/dataset-freeze.json',
                'docs/phase-6/openai-profile-freeze.json',
                'docs/phase-8/OPERATOR-GUIDE.md',
                'automation/n8n/intake-v1.json',
                'automation/n8n/due-v1.json'} <= names
        assert not any(name.startswith('local/') or name == '.env' for name in names)
        for workflow in ('intake', 'due'):
            assert json.loads(archive.read(f'automation/n8n/{workflow}-v1.json'))['active'] is False


@pytest.mark.parametrize('name', ['../escape', 'x/../escape', '/absolute', 'C:/drive'])
def test_verifier_rejects_unsafe_paths(tmp_path, name):
    archive_path = tmp_path / 'unsafe.zip'
    with zipfile.ZipFile(archive_path, 'w') as archive:
        archive.writestr(name, 'x')
        archive.writestr('release-manifest.json', json.dumps({'files': {name: ''}}))
    with pytest.raises(ValueError, match='Unsafe archive path'):
        verify(archive_path)
