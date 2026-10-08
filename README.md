# Camera Viewer Lite

A standalone Windows camera viewer using PyQt5 and OpenCV, with live display,
exposure and gain controls, saving, image processing, beam profiling, and
per-camera alignment references.

## Download

You do not need the source code, Python, Conda, pip, or internet access on the
target computer.

- [Download the latest Windows installer](../../releases/latest/download/CameraViewer-Setup-win64.exe)
- [Download the latest portable ZIP](../../releases/latest/download/CameraViewer-Portable-win64.zip)
- [Verify SHA-256 checksums](../../releases/latest/download/SHA256SUMS.txt)

The release targets 64-bit Windows 10 and Windows 11. Standard USB/UVC cameras
use Windows DirectShow. Cameras that require a manufacturer driver still need
that Windows driver installed separately.

The installer is per-user and does not require administrator rights. The
executables are currently unsigned, so Windows SmartScreen may show an
**Unknown publisher** warning.

## Build from source

On a 64-bit Windows development computer with Python 3.12:

```powershell
.\distribution\bootstrap_build_env.ps1
.\distribution\build_release.ps1
```

Release artifacts are written to `artifacts/`. Generated binaries are not
committed to Git; tagged releases are built and attached automatically by
GitHub Actions.

See [standalone distribution documentation](distribution/README.md) for build
and clean-PC acceptance testing, and [GitHub release instructions](GITHUB_RELEASES.md)
for the one-time remote setup and future releases.

