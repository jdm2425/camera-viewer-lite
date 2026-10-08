"""Publish a tested onedir build. Never overwrite an existing release."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('version')
    parser.add_argument('--destination', required=True)
    parser.add_argument('--build-dir', type=Path,
                        help='Optional locally tested application directory')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9._-]+', args.version) or args.version in ('.', '..'):
        parser.error('Use a simple version identifier')
    root = Path(__file__).resolve().parents[1]
    destination = Path(args.destination)
    releases = destination / 'releases'
    releases.mkdir(parents=True, exist_ok=True)
    archive = releases / (args.version + '.zip')
    if archive.exists():
        raise FileExistsError('Release already exists; use a new version')
    app = args.build_dir or root / 'dist' / 'CameraViewer'
    if not (app / 'CameraViewer.exe').is_file():
        raise FileNotFoundError('Build CameraViewer first')
    # Compress locally; send one file to the NAS rather than many small writes.
    with tempfile.TemporaryDirectory(prefix='cv-publish-') as temporary:
        local_archive = shutil.make_archive(str(Path(temporary) / 'release'), 'zip', app)
        partial = archive.with_suffix('.zip.partial')
        shutil.copyfile(local_archive, partial)
        partial.rename(archive)
    with archive.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    shutil.copy2(root / 'dist' / 'CameraViewerLauncher.exe',
                 destination / 'Install Camera Viewer.exe')
    manifest = destination / 'current.json.tmp'
    manifest.write_text(json.dumps({'version': args.version, 'sha256': digest}, indent=2))
    shutil.copy2(manifest, releases / (args.version + '.json'))
    os.replace(manifest, destination / 'current.json')


if __name__ == '__main__':
    main()
