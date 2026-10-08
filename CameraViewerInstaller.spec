# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path


root = Path(SPECPATH)
payload = root / 'dist' / 'CameraViewer'
if not (payload / 'CameraViewer.exe').is_file():
    raise FileNotFoundError('Build CameraViewer.spec before building the installer')

a = Analysis(
    ['distribution/local_installer.py'],
    pathex=[str(root)],
    binaries=[],
    datas=[
        (str(payload), 'payload/CameraViewer'),
        (str(root / 'distribution' / 'uninstall.ps1'), '.'),
        (str(root / 'distribution' / 'VERSION'), '.'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='CameraViewer-Setup',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

