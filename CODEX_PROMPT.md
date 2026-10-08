# Camera Viewer Lite

You are working on an extracted version of a much larger Python project.

The objective is NOT to improve the original project.

The objective is to produce a clean standalone application that only contains the code required for Camera Viewer.

## Current state

The application successfully launches using

    python -m lab_apps.scripts.pointlock.camera_viewer

The GUI opens.

The extraction has already been completed manually.

The project currently contains additional folders such as

- hardware
- physdata
- mathx

that were copied wholesale because they contained dependencies.

These folders should eventually be reduced to only the files actually required.

Do NOT remove files unless you have verified they are unused.

---

## Primary goals

Priority 1

Maintain a working application.

Never sacrifice functionality for cleanliness.

---

Priority 2

Reduce the codebase.

Use static analysis and runtime imports to determine unused files.

Avoid deleting files that may be dynamically imported.

---

Priority 3

Improve the GUI.

Modernise appearance while preserving functionality.

Avoid changing application behaviour unless fixing bugs.

---

Priority 4

Package the application.

Use PyInstaller.

First create a stable

    --onedir

build.

Later create

    --onefile

if practical.

---

## Coding style

Prefer small readable functions.

Avoid introducing unnecessary abstractions.

Do not rewrite working code.

Refactor only where it improves maintainability.

---

## When fixing bugs

Always determine why the bug occurs.

Prefer fixing root causes rather than adding workarounds.

---

## When removing code

Be conservative.

Only remove code that has been demonstrated to be unused.

---

## Deliverables

Eventually produce

- camera_viewer_lite
- requirements.txt
- environment.yml
- PyInstaller spec file
- executable build

The application should run on another Windows PC with only the generated environment and executable.