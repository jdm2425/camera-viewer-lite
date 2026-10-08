import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    'desktop_launcher', Path(__file__).resolve().parents[1] / 'distribution' / 'desktop_launcher.py')
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


class DistributionTests(unittest.TestCase):
    def test_download_cache_and_hash_rejection(self):
        with tempfile.TemporaryDirectory() as folder:
            nas = Path(folder) / 'nas'
            cache = Path(folder) / 'cache'
            (nas / 'releases').mkdir(parents=True)
            cache.mkdir()
            archive = nas / 'releases' / 'test1.zip'
            with zipfile.ZipFile(archive, 'w') as zipped:
                zipped.writestr('CameraViewer.exe', b'test executable')
            manifest = {'version': 'test1', 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}
            (nas / 'current.json').write_text(json.dumps(manifest))
            with patch.object(launcher, 'NAS', nas), patch.object(launcher, 'CACHE', cache):
                target = launcher.latest_release()
                self.assertEqual((target / 'CameraViewer.exe').read_bytes(), b'test executable')
                archive.unlink()
                self.assertEqual(launcher.latest_release(), target)
                manifest['version'] = 'test2'
                archive = nas / 'releases' / 'test2.zip'
                archive.write_bytes(b'corrupted')
                (nas / 'current.json').write_text(json.dumps(manifest))
                with self.assertRaisesRegex(ValueError, 'checksum'):
                    launcher.latest_release()
                self.assertEqual(json.loads((cache / 'cached.json').read_text())['version'], 'test1')


if __name__ == '__main__':
    unittest.main()
