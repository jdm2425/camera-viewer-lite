# Camera Viewer Lite

## Purpose

This project is a lightweight extraction of the original Pointlock codebase.

The objective is to isolate only the functionality required to run

    lab_apps.scripts.pointlock.camera_viewer

without the rest of the Pointlock software.

The long-term goal is to produce a standalone executable that can be distributed to another PC.

---

## Current Status

The application runs independently from the original codebase and has a
reproducible Windows release pipeline.

It launches successfully using

    python -m lab_apps.scripts.pointlock.camera_viewer

from inside

    camera_viewer_lite/

The GUI opens successfully, and the frozen executable has an automated
offscreen startup check. Real-camera operation must still be checked on the
target hardware for each release.

---

## Build and distribution

Create the pinned build environment and produce both an offline installer and
portable ZIP:

    .\distribution\bootstrap_build_env.ps1
    .\distribution\build_release.ps1

Release files are written to `artifacts/`. Target computers do not need Python,
Conda, pip, internet access, or the repository. See `distribution/README.md`
for deployment and clean-PC acceptance testing.

---

## Current project structure

camera_viewer_lite/

contains

- lab_apps/
- hardware/
- physdata/
- mathx/
- fourier.py

plus launcher utilities.

Some folders (hardware, physdata) currently contain many more files than are likely required.

These should eventually be reduced.

---

## Distribution outputs

- `CameraViewer-Setup-<version>-win64.exe` — local per-user installer.
- `CameraViewer-Portable-<version>-win64.zip` — extract-and-run package.
- `SHA256SUMS-<version>.txt` — release integrity hashes.
