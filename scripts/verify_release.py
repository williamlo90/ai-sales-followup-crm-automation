"""Verify a local delivery ZIP and optionally extract to a fresh directory."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path


def verify(archive_path, extract_to=None):
    archive_path = Path(archive_path).resolve()
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or 'release-manifest.json' not in names:
            raise ValueError('Duplicate entries or missing manifest')
        for name in names:
            parts = name.split('/')
            if (not name or name.startswith('/') or '\\' in name or ':' in parts[0]
                    or any(part in {'', '.', '..'} for part in parts)):
                raise ValueError('Unsafe archive path')
        manifest = json.loads(archive.read('release-manifest.json'))
        expected = manifest['files']
        if set(names) != set(expected) | {'release-manifest.json'}:
            raise ValueError('Manifest file set mismatch')
        for name, digest in expected.items():
            if hashlib.sha256(archive.read(name)).hexdigest() != digest:
                raise ValueError('Manifest hash mismatch: ' + name)
        if extract_to is not None:
            target = Path(extract_to).resolve()
            if target.exists() and any(target.iterdir()):
                raise ValueError('Extraction directory must be empty')
            target.mkdir(parents=True, exist_ok=True)
            archive.extractall(target)
    return {'status': 'verified', 'files': len(expected),
            'archive_sha256': hashlib.sha256(archive_path.read_bytes()).hexdigest(),
            'extracted_to': str(Path(extract_to).resolve()) if extract_to else None}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('archive')
    parser.add_argument('--extract-to')
    args = parser.parse_args()
    print(json.dumps(verify(args.archive, args.extract_to), indent=2))
