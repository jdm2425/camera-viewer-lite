"""Offline, per-user launcher. Release archives are immutable."""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import zipfile

NAS = Path(r'\\ROLNAS\Roland Group NAS\Software\CameraViewer2026')
CACHE = Path(os.environ['LOCALAPPDATA']) / 'CameraViewer2026'


def message(text):
    ctypes.windll.user32.MessageBoxW(None, text, 'Camera Viewer', 0)


def install():
    CACHE.mkdir(parents=True, exist_ok=True)
    target = CACHE / 'CameraViewerLauncher.exe'
    if Path(sys.executable).resolve() != target.resolve():
        shutil.copy2(sys.executable, target)
    # Values are passed via environment variables, never interpolated as code.
    env = dict(os.environ, CV_TARGET=str(target))
    script = (
        '$w = New-Object -ComObject WScript.Shell; '
        '$s = $w.CreateShortcut((Join-Path ([Environment]::GetFolderPath('
        "'Desktop')) 'Camera Viewer.lnk')); "
        '$s.TargetPath = $env:CV_TARGET; $s.Save()'
    )
    subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script],
                   env=env, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
    message('Installed. Use the Camera Viewer desktop shortcut. '
            'The first launch needs access to the NAS.')


def latest_release():
    manifest = json.loads((NAS / 'current.json').read_text(encoding='utf-8'))
    version = manifest['version']
    if not re.fullmatch(r'[A-Za-z0-9._-]+', version) or version in ('.', '..'):
        raise ValueError('Invalid release version')
    archive = NAS / 'releases' / (version + '.zip')
    target = CACHE / 'releases' / version
    if not (target / 'CameraViewer.exe').is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=target.parent) as temporary:
            local = Path(temporary) / 'release.zip'
            shutil.copyfile(archive, local)
            with local.open('rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            if digest != manifest['sha256']:
                raise ValueError('Release checksum mismatch')
            unpacked = Path(temporary) / 'app'
            unpacked.mkdir()
            with zipfile.ZipFile(local) as zipped:
                for item in zipped.infolist():
                    path = (unpacked / item.filename).resolve()
                    if not path.is_relative_to(unpacked.resolve()):
                        raise ValueError('Unsafe archive path')
                zipped.extractall(unpacked)
            if not (unpacked / 'CameraViewer.exe').is_file():
                raise ValueError('Release has no application executable')
            try:
                unpacked.rename(target)
            except FileExistsError:
                if not (target / 'CameraViewer.exe').is_file():
                    raise
    pointer = CACHE / 'cached.json'
    temporary_pointer = CACHE / ('cached-' + str(os.getpid()) + '.tmp')
    temporary_pointer.write_text(json.dumps({'version': version}), encoding='utf-8')
    os.replace(temporary_pointer, pointer)
    return target


def main():
    try:
        if '--self-test' in sys.argv:
            import tkinter as tk
            window = tk.Tk()
            window.withdraw()
            window.update()
            window.destroy()
            return
        if '--install' in sys.argv or Path(sys.executable).name.startswith('Install'):
            install()
            return
        CACHE.mkdir(parents=True, exist_ok=True)
        launch_with_progress()
    except Exception as error:
        if '--self-test' in sys.argv:
            raise
        message('Camera Viewer could not start. Connect to the NAS and retry.\n\n' + str(error))


def launch_with_progress():
    import tkinter as tk
    from tkinter import ttk
    window = tk.Tk()
    window.title('Camera Viewer')
    window.geometry('440x120')
    window.resizable(False, False)
    ttk.Label(window, text='Checking the NAS and preparing Camera Viewer...').pack(pady=15)
    progress = ttk.Progressbar(window, mode='indeterminate', length=390)
    progress.pack()
    progress.start()
    result = []

    def prepare():
        try:
            try:
                target = latest_release()
            except Exception as error:
                (CACHE / 'update-error.txt').write_text(str(error), encoding='utf-8')
                pointer = json.loads((CACHE / 'cached.json').read_text())
                version = pointer['version']
                if not re.fullmatch(r'[A-Za-z0-9._-]+', version) or version in ('.', '..'):
                    raise ValueError('Invalid cached release')
                target = CACHE / 'releases' / version
            result.append(target)
        except Exception as error:
            result.append(error)

    def check():
        if not result:
            window.after(100, check)
            return
        window.destroy()

    threading.Thread(target=prepare, daemon=True).start()
    window.after(100, check)
    window.mainloop()
    if not result:
        return
    if isinstance(result[0], Exception):
        raise result[0]
    subprocess.Popen([str(result[0] / 'CameraViewer.exe')], cwd=result[0])


if __name__ == '__main__':
    main()
