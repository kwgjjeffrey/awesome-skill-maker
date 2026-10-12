#!/usr/bin/env python3
"""Verify a downloaded Skill archive before running its managed installer."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('archive', 'manifest', 'target', 'store'):
        p.add_argument('--' + key, required=True)
    a = p.parse_args()
    m = json.loads(Path(a.manifest).read_text())
    archive = Path(a.archive).resolve()
    if archive.stat().st_size != m['size'] or hashlib.sha256(archive.read_bytes()).hexdigest() != m['sha256']:
        raise ValueError('Archive size/SHA-256 mismatch')
    with tempfile.TemporaryDirectory(prefix='skill-bootstrap-') as tmp:
        destination = Path(tmp).resolve()
        with tarfile.open(archive, 'r:gz') as bundle:
            members = bundle.getmembers()
            if len(members) > 10000 or sum(x.size for x in members) > 200_000_000:
                raise ValueError('Archive exceeds limits')
            names = set()
            for x in members:
                if x.name in names or '\\' in x.name or x.name.split('/')[0] != 'package' or '..' in x.name.split('/') or not (x.isfile() or x.isdir()) or not (destination / x.name).resolve().is_relative_to(destination):
                    raise ValueError('Unsafe archive entry')
                names.add(x.name)
            for x in members:
                output = destination / x.name
                if x.isdir():
                    output.mkdir(parents=True, exist_ok=True)
                else:
                    output.parent.mkdir(parents=True, exist_ok=True)
                    with bundle.extractfile(x) as source, output.open('wb') as sink:
                        import shutil
                        shutil.copyfileobj(source, sink)
        subprocess.run([sys.executable, str(destination / 'package/setup/scripts/manage_skill_installation.py'), 'install', '--archive', str(archive), '--manifest', str(Path(a.manifest).resolve()), '--target', a.target, '--store', a.store], check=True)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, tarfile.TarError, subprocess.CalledProcessError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
