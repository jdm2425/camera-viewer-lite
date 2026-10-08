import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location(
    "local_installer",
    Path(__file__).resolve().parents[1] / "distribution" / "local_installer.py",
)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class LocalInstallerTests(unittest.TestCase):
    def test_install_replaces_payload_and_writes_version(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            resources = root / "resources"
            payload = resources / "payload" / "CameraViewer"
            payload.mkdir(parents=True)
            (payload / "CameraViewer.exe").write_bytes(b"new executable")
            (payload / "_internal").mkdir()
            (payload / "_internal" / "dependency.dll").write_bytes(b"dependency")
            (resources / "VERSION").write_text("1.2.3\n", encoding="utf-8")
            (resources / "uninstall.ps1").write_text("# uninstall", encoding="utf-8")
            target = root / "installed"
            target.mkdir()
            (target / "CameraViewer.exe").write_bytes(b"old executable")

            def resource(name):
                return resources / Path(name)

            with (
                patch.object(installer, "bundled_path", side_effect=resource),
                patch.object(installer, "windows_folder", return_value=root / "shortcuts"),
                patch.object(installer, "create_shortcut"),
                patch.object(installer, "register_uninstaller"),
            ):
                executable, version = installer.install(target)

            self.assertEqual(version, "1.2.3")
            self.assertEqual(executable.read_bytes(), b"new executable")
            self.assertTrue((target / "_internal" / "dependency.dll").is_file())
            self.assertEqual(
                json.loads((target / "install.json").read_text(encoding="utf-8")),
                {"version": "1.2.3"},
            )


if __name__ == "__main__":
    unittest.main()

