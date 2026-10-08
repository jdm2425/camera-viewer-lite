$ErrorActionPreference = "SilentlyContinue"
$installRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$desktopShortcut = Join-Path ([Environment]::GetFolderPath("Desktop")) "Camera Viewer.lnk"
$startMenuFolder = Join-Path ([Environment]::GetFolderPath("Programs")) "Camera Viewer"

Remove-Item -LiteralPath $desktopShortcut -Force
Remove-Item -LiteralPath $startMenuFolder -Recurse -Force
Remove-Item -LiteralPath "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\CameraViewerLite" -Recurse -Force

$temporaryScript = Join-Path $env:TEMP ("camera-viewer-uninstall-" + [guid]::NewGuid().ToString("N") + ".ps1")
$escapedRoot = $installRoot.Replace("'", "''")
$cleanup = @"
Start-Sleep -Milliseconds 500
Remove-Item -LiteralPath '$escapedRoot' -Recurse -Force
Remove-Item -LiteralPath `$MyInvocation.MyCommand.Path -Force
"@
Set-Content -LiteralPath $temporaryScript -Value $cleanup -Encoding UTF8
Start-Process powershell.exe -WindowStyle Hidden -ArgumentList @(
    "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
    "-File", $temporaryScript
)

