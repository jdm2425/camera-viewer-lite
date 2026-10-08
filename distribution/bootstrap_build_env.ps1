[CmdletBinding()]
param(
    [string]$Python = "python",
    [switch]$Recreate
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$venv = Join-Path $repoRoot ".venv"
$venvPython = Join-Path $venv "Scripts\python.exe"

if ($Recreate -and (Test-Path -LiteralPath $venv)) {
    $resolvedVenv = (Resolve-Path -LiteralPath $venv).Path
    if (-not $resolvedVenv.StartsWith($repoRoot, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove a virtual environment outside the repository."
    }
    Remove-Item -LiteralPath $resolvedVenv -Recurse -Force
}

if (-not (Test-Path -LiteralPath $venvPython)) {
    & $Python -m venv $venv
    if ($LASTEXITCODE -ne 0) {
        throw "Could not create .venv with '$Python'. Install 64-bit Python 3.12 and retry."
    }
}

& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Could not update pip." }

& $venvPython -m pip install -r (Join-Path $repoRoot "requirements-build.txt")
if ($LASTEXITCODE -ne 0) { throw "Could not install the build dependencies." }

Write-Host "Build environment ready: $venvPython"
Write-Host "Next: .\distribution\build_release.ps1"

