# GitHub repository and releases

This repository is prepared for GitHub, but the remote repository must be
created in the GitHub account or organisation that will own it.

## First-time GitHub setup

1. Sign in to GitHub and create a new **empty** repository named
   `camera-viewer-lite`. Choose public or private as appropriate. Do not add a
   README, `.gitignore`, or licence on GitHub because they already exist here.
2. From this repository directory, connect and push it (replace `OWNER`):

   ```powershell
   git remote add origin https://github.com/OWNER/camera-viewer-lite.git
   git push -u origin main
   git push origin v1.0.0
   ```

3. Open the repository's **Actions** page. The `v1.0.0` tag starts the Windows
   build. After it passes, GitHub creates the release and uploads the installer,
   portable ZIP, and checksums.

The workflow declares `contents: write`, which normally gives its automatic
`GITHUB_TOKEN` permission to create the release. If an organisation policy
overrides it, enable read/write workflow permissions under **Settings > Actions
> General > Workflow permissions**.

## Publishing a later version

First commit and push all code changes. With a clean working tree, run:

```powershell
.\distribution\new_release.ps1 -Version 1.0.1
```

The helper updates `distribution/VERSION`, commits it, creates the matching
`v1.0.1` tag, and pushes both the branch and tag. The tag triggers a clean
Windows build on GitHub. Tests and the packaged GUI smoke test must pass before
the release is published, so the downloadable installer always corresponds to
that exact tagged source revision.

Never move or reuse a release tag. If a release is wrong, fix the code and
publish a higher version.

## Download links

On GitHub, users can open the repository's **Releases** page without cloning or
downloading the source. These stable relative links always resolve to the newest
published release:

- [Latest installer](../../releases/latest/download/CameraViewer-Setup-win64.exe)
- [Latest portable ZIP](../../releases/latest/download/CameraViewer-Portable-win64.zip)
- [Latest checksums](../../releases/latest/download/SHA256SUMS.txt)

GitHub also provides version-specific release pages and automatically marks the
new workflow-created release as the latest.

