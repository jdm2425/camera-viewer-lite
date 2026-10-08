CAMERA VIEWER - OFFLINE WINDOWS RELEASE
=======================================

SUPPORTED SYSTEMS
  64-bit Windows 10 or Windows 11.

INSTALLER
  Run CameraViewer-Setup-<version>.exe. It installs for the current Windows
  user, adds Desktop and Start Menu shortcuts, and does not need administrator
  access. Python, Conda, pip, and internet access are not required.

PORTABLE VERSION
  Extract the entire ZIP before use, then run "Run Camera Viewer.cmd" or
  CameraViewer.exe. Do not move CameraViewer.exe away from its _internal
  directory.

CAMERAS
  Standard USB/UVC cameras use the Windows DirectShow driver. A camera that
  requires a manufacturer driver still needs that Windows driver installed.
  Drivers cannot safely be bundled without knowing the exact camera model and
  its vendor licence.

UNINSTALL
  Use Windows Settings > Apps > Installed apps > Camera Viewer, or run
  "Uninstall Camera Viewer" from its Start Menu folder.

SECURITY NOTICE
  The executables are not code-signed. Windows SmartScreen may show an
  Unknown publisher warning until the release is signed with an Authenticode
  certificate.

