[CmdletBinding()]
param(
    [string]$Python,
    [switch]$SkipTests,
    [switch]$ReuseAppBuild,
    [switch]$SkipSmokeTest
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $Python) {
    $Python = Join-Path $repoRoot ".venv\Scripts\python.exe"
}
if (-not (Test-Path -LiteralPath $Python)) {
    throw "Build Python not found at '$Python'. Run .\distribution\bootstrap_build_env.ps1 first."
}

$version = (Get-Content -LiteralPath (Join-Path $PSScriptRoot "VERSION") -Raw).Trim()
if ($version -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]*$') {
    throw "distribution/VERSION contains an invalid version."
}

$appDist = Join-Path $repoRoot "dist\CameraViewer"
$appExe = Join-Path $appDist "CameraViewer.exe"
$artifacts = Join-Path $repoRoot "artifacts"
$portableRoot = Join-Path $repoRoot "build\portable\CameraViewer-$version"

Push-Location $repoRoot
try {
    if (-not $SkipTests) {
        & $Python -m unittest discover -s tests -v
        if ($LASTEXITCODE -ne 0) { throw "Tests failed." }
    }

    if (-not $ReuseAppBuild) {
        & $Python -m PyInstaller --noconfirm --clean CameraViewer.spec
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $appExe)) {
            throw "The Camera Viewer application build failed."
        }
    } elseif (-not (Test-Path -LiteralPath $appExe)) {
        throw "-ReuseAppBuild was specified but dist/CameraViewer/CameraViewer.exe does not exist."
    }

    if (-not $SkipSmokeTest) {
        $smokeReport = Join-Path $env:TEMP ("camera-viewer-smoke-" + [guid]::NewGuid().ToString("N") + ".txt")
        $oldQtPlatform = $env:QT_QPA_PLATFORM
        try {
            $env:QT_QPA_PLATFORM = "offscreen"
            $process = Start-Process -FilePath $appExe -ArgumentList @(
                "--smoke-test", "--smoke-report", $smokeReport
            ) -WorkingDirectory $appDist -Wait -PassThru
            if ($process.ExitCode -ne 0 -or (Test-Path -LiteralPath $smokeReport)) {
                $details = if (Test-Path -LiteralPath $smokeReport) {
                    Get-Content -LiteralPath $smokeReport -Raw
                } else {
                    "Process exit code: $($process.ExitCode)"
                }
                throw "The frozen application smoke test failed.`n$details"
            }
        } finally {
            if ($null -eq $oldQtPlatform) {
                Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
            } else {
                $env:QT_QPA_PLATFORM = $oldQtPlatform
            }
            Remove-Item -LiteralPath $smokeReport -Force -ErrorAction SilentlyContinue
        }
    }

    New-Item -ItemType Directory -Path $artifacts -Force | Out-Null
    if (Test-Path -LiteralPath $portableRoot) {
        $resolvedPortable = (Resolve-Path -LiteralPath $portableRoot).Path
        $allowedPortableRoot = (Join-Path $repoRoot "build\portable")
        if (-not $resolvedPortable.StartsWith($allowedPortableRoot, [StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to clean a portable directory outside build/portable."
        }
        Remove-Item -LiteralPath $resolvedPortable -Recurse -Force
    }
    New-Item -ItemType Directory -Path $portableRoot -Force | Out-Null
    Copy-Item -Path (Join-Path $appDist "*") -Destination $portableRoot -Recurse -Force
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot "portable_runner.cmd") -Destination (Join-Path $portableRoot "Run Camera Viewer.cmd")
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot "OFFLINE_README.txt") -Destination (Join-Path $portableRoot "README.txt")

    $portableZip = Join-Path $artifacts "CameraViewer-Portable-$version-win64.zip"
    Remove-Item -LiteralPath $portableZip -Force -ErrorAction SilentlyContinue
    Compress-Archive -Path $portableRoot -DestinationPath $portableZip -CompressionLevel Optimal

    & $Python -m PyInstaller --noconfirm --clean --distpath $artifacts --workpath (Join-Path $repoRoot "build\installer") CameraViewerInstaller.spec
    if ($LASTEXITCODE -ne 0) { throw "The offline installer build failed." }
    $rawSetup = Join-Path $artifacts "CameraViewer-Setup.exe"
    $versionedSetup = Join-Path $artifacts "CameraViewer-Setup-$version-win64.exe"
    Move-Item -LiteralPath $rawSetup -Destination $versionedSetup -Force

    $hashFile = Join-Path $artifacts "SHA256SUMS-$version.txt"
    $hashLines = @()
    foreach ($file in @($versionedSetup, $portableZip)) {
        $hash = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
        $hashLines += "$hash  $([IO.Path]::GetFileName($file))"
    }
    Set-Content -LiteralPath $hashFile -Value $hashLines -Encoding ASCII

    Write-Host "Release $version built successfully:"
    Write-Host "  $versionedSetup"
    Write-Host "  $portableZip"
    Write-Host "  $hashFile"
} finally {
    Pop-Location
}
