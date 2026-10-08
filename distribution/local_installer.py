"""Per-user offline installer for the frozen Camera Viewer application."""

import argparse
import ctypes
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import uuid
import winreg


APP_NAME = "Camera Viewer"
APP_ID = "CameraViewerLite"
UNINSTALL_KEY = (
    r"Software\Microsoft\Windows\CurrentVersion\Uninstall" + "\\" + APP_ID
)


def bundled_path(name):
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / name


def default_install_dir():
    return Path(os.environ["LOCALAPPDATA"]) / "Programs" / "CameraViewer"


def message(text, flags=0):
    return ctypes.windll.user32.MessageBoxW(None, text, APP_NAME, flags)


def windows_folder(csidl):
    buffer = ctypes.create_unicode_buffer(260)
    result = ctypes.windll.shell32.SHGetFolderPathW(None, csidl, None, 0, buffer)
    if result != 0:
        raise OSError(result, "Windows could not locate a user shell folder")
    return Path(buffer.value)


def create_shortcut(shortcut, executable, arguments="", icon=None):
    shortcut.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["CV_SHORTCUT"] = str(shortcut)
    env["CV_EXECUTABLE"] = str(executable)
    env["CV_ARGUMENTS"] = arguments
    env["CV_ICON"] = str(icon or executable)
    script = (
        "$w = New-Object -ComObject WScript.Shell; "
        "$s = $w.CreateShortcut($env:CV_SHORTCUT); "
        "$s.TargetPath = $env:CV_EXECUTABLE; "
        "$s.WorkingDirectory = Split-Path $env:CV_EXECUTABLE; "
        "$s.Arguments = $env:CV_ARGUMENTS; "
        "$s.IconLocation = $env:CV_ICON; "
        "$s.Save()"
    )
    subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        env=env,
        check=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


def register_uninstaller(install_dir, version):
    uninstall_command = (
        f'powershell.exe -NoProfile -ExecutionPolicy Bypass -File '
        f'"{install_dir / "uninstall.ps1"}"'
    )
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY) as key:
        values = {
            "DisplayName": APP_NAME,
            "DisplayVersion": version,
            "Publisher": "Camera Viewer Lite",
            "DisplayIcon": str(install_dir / "CameraViewer.exe"),
            "InstallLocation": str(install_dir),
            "UninstallString": uninstall_command,
            "QuietUninstallString": uninstall_command,
        }
        for name, value in values.items():
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
        winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)


def install(install_dir):
    payload = bundled_path("payload/CameraViewer")
    source_uninstaller = bundled_path("uninstall.ps1")
    version = bundled_path("VERSION").read_text(encoding="utf-8").strip()
    if not (payload / "CameraViewer.exe").is_file():
        raise FileNotFoundError("The installer payload is incomplete.")

    install_dir = install_dir.resolve()
    install_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = install_dir.parent / (".CameraViewer-install-" + uuid.uuid4().hex)
    backup = install_dir.parent / (".CameraViewer-backup-" + uuid.uuid4().hex)
    try:
        shutil.copytree(payload, staging)
        shutil.copy2(source_uninstaller, staging / "uninstall.ps1")
        (staging / "install.json").write_text(
            json.dumps({"version": version}, indent=2), encoding="utf-8"
        )
        if install_dir.exists():
            install_dir.rename(backup)
        staging.rename(install_dir)
    except Exception:
        if not install_dir.exists() and backup.exists():
            backup.rename(install_dir)
        raise
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)

    executable = install_dir / "CameraViewer.exe"
    desktop = windows_folder(0x10) / "Camera Viewer.lnk"
    programs = windows_folder(0x02)
    start_menu = programs / "Camera Viewer"
    create_shortcut(desktop, executable)
    create_shortcut(start_menu / "Camera Viewer.lnk", executable)
    create_shortcut(
        start_menu / "Uninstall Camera Viewer.lnk",
        Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe",
        '-NoProfile -ExecutionPolicy Bypass -File "{}"'.format(
            install_dir / "uninstall.ps1"
        ),
        icon=executable,
    )
    register_uninstaller(install_dir, version)
    if backup.exists():
        shutil.rmtree(backup, ignore_errors=True)
    return executable, version


def main():
    parser = argparse.ArgumentParser(description="Install Camera Viewer locally.")
    parser.add_argument("--install-dir", type=Path, default=default_install_dir())
    parser.add_argument("--silent", action="store_true")
    parser.add_argument("--no-launch", action="store_true")
    args = parser.parse_args()

    try:
        if platform.machine().lower() not in {"amd64", "x86_64"}:
            raise RuntimeError("Camera Viewer requires 64-bit Windows.")
        executable, version = install(args.install_dir)
        if not args.silent:
            message(f"Camera Viewer {version} was installed successfully.")
        if not args.no_launch:
            subprocess.Popen([str(executable)], cwd=executable.parent)
    except Exception as error:
        if args.silent:
            raise
        message("Camera Viewer could not be installed.\n\n" + str(error), 0x10)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
