# Camera Viewer Lite TODO

## Phase 1

Verify every feature works.

Check every button.

Record failures.

---

## Phase 2

Reduce project size.

Identify

- unused Python files
- unused packages
- unused resources

Do not remove files blindly.

Only remove files after confirming they are never imported.

---

## Phase 3

Improve GUI.

Possible work

- layout
- resizing
- labels
- button grouping
- spacing
- fonts

Maintain existing functionality.

---

## Phase 4

Packaging

Create a PyInstaller build.

Prefer

    --onedir

until stable.

Later switch to

    --onefile

---

## Phase 5

Environment

Generate

requirements.txt

and

environment.yml

that reproduce the project.

---

## Nice to have

Improve the extraction tool.

It currently misses

- top-level modules
- package-level imports

These improvements are lower priority than the application itself.