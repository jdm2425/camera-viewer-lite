# Standalone Windows distribution

Camera Viewer is packaged as a **64-bit Windows onedir application**. The
frozen directory contains Python and every Python/native library used by the
program. A target PC does not need Python, Conda, pip, an internet connection,
or access to the source repository.

The build produces two equivalent offline deliverables:

- `CameraViewer-Setup-<version>-win64.exe`: single-file, per-user installer.
- `CameraViewer-Portable-<version>-win64.zip`: extract-and-run fallback.

Both are checksummed in `artifacts/SHA256SUMS-<version>.txt`.

## Supported target

- 64-bit Windows 10 or Windows 11.
- A standard USB/UVC camera supported by Windows DirectShow.
- Enough free space for the extracted application and temporary installer
  payload (allow roughly three times the portable application's size while
  installing).

The application itself is offline and self-contained. Manufacturer-specific
camera drivers are operating-system drivers, not Python dependencies, and must
be installed separately if the camera is not supported natively by Windows.

## Build a release

Use a 64-bit Windows development PC with 64-bit Python 3.12 and internet access
for the one-time dependency download:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\distribution\bootstrap_build_env.ps1
.\distribution\build_release.ps1
```

`bootstrap_build_env.ps1` creates `.venv` and installs the pinned dependencies
from `requirements-build.txt`. Subsequent builds are offline as long as that
environment remains present. To select a particular Python executable:

```powershell
.\distribution\bootstrap_build_env.ps1 -Python "C:\Python312\python.exe"
```

Before packaging, `build_release.ps1` runs the unit tests, performs a clean
PyInstaller build, and launches the frozen GUI using Qt's offscreen backend as
a startup smoke test. It only emits release artifacts after those checks pass.

The release version comes from `distribution/VERSION`. Change it before making
a new public release; do not overwrite an already distributed version.

## Install and run

Copy the setup EXE to the destination PC by USB drive, shared folder, or your
normal software-distribution system, then run it. Installation is under:

```text
%LOCALAPPDATA%\Programs\CameraViewer
```

It does not request administrator access. It creates Desktop and Start Menu
shortcuts and adds Camera Viewer to the current user's Installed Apps list.
Settings and saved camera names use the user's normal Qt/Windows settings area,
so application upgrades do not erase them.

For the portable edition, extract the entire ZIP and run
`Run Camera Viewer.cmd`. `CameraViewer.exe` must remain beside `_internal`.

## Acceptance test on a clean PC

Test every release on a representative Windows PC or clean Windows VM that has
never had Python or Conda installed:

1. Disconnect it from the internet and install from the setup EXE.
2. Start Camera Viewer from both shortcuts.
3. Connect the intended camera, select **Rescan**, then **Connect**.
4. Confirm live frames, exposure/gain controls, image saving, and beam profile.
5. Restart Windows and repeat a launch and camera connection.
6. Uninstall from Windows Settings and confirm the shortcuts are removed.

This hardware acceptance test is essential: an offscreen smoke test verifies
the bundled software but cannot validate a real camera or its Windows driver.

## Signing

The generated executables are unsigned, so SmartScreen can show **Unknown
publisher**. For broad deployment, sign both EXEs with your organisation's
Authenticode certificate after building and before publishing checksums.

## Legacy NAS updater

`desktop_launcher.py`, `publish.py`, `CameraViewerLauncher.spec`, and the old
NAS manifest workflow remain in the repository for existing deployments. They
are not used by the standalone local installer and are not required on a new
PC.

