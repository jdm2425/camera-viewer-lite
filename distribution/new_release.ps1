[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9]+\.[0-9]+\.[0-9]+(?:[-.][A-Za-z0-9.-]+)?$')]
    [string]$Version,
    [string]$Remote = "origin",
    [string]$Branch = "main"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Push-Location $repoRoot
try {
    git rev-parse --is-inside-work-tree | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "This directory is not a Git repository." }

    $changes = git status --porcelain
    if ($changes) {
        throw "Commit or discard the current working-tree changes before creating a release."
    }

    git remote get-url $Remote | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Git remote '$Remote' is not configured." }

    $tag = "v$Version"
    git rev-parse --verify --quiet "refs/tags/$tag" | Out-Null
    if ($LASTEXITCODE -eq 0) { throw "Tag '$tag' already exists. Use a new version." }

    Set-Content -LiteralPath (Join-Path $PSScriptRoot "VERSION") -Value $Version -Encoding ASCII
    git add distribution/VERSION
    git commit -m "Release $Version"
    if ($LASTEXITCODE -ne 0) { throw "Could not commit the version change." }

    git tag -a $tag -m "Camera Viewer $Version"
    if ($LASTEXITCODE -ne 0) { throw "Could not create tag '$tag'." }

    git push $Remote $Branch
    if ($LASTEXITCODE -ne 0) { throw "Could not push branch '$Branch'." }
    git push $Remote $tag
    if ($LASTEXITCODE -ne 0) { throw "Could not push tag '$tag'." }

    Write-Host "Release requested. Track it at:"
    $url = git remote get-url $Remote
    if ($url -match '^https://github\.com/(.+?)(?:\.git)?$') {
        Write-Host "https://github.com/$($Matches[1])/actions"
    } else {
        Write-Host "the Actions page of the remote repository"
    }
} finally {
    Pop-Location
}

