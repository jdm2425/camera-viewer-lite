# Release notes

## 2026.09.11.003

- Restores the fast camera-driver automatic exposure as **Camera auto**.
- Retains the saturation-checked algorithm as a separate optional
  **Safe exposure scan**, so it no longer blocks routine auto-exposure use.
- Remembers the Camera auto toggle separately for each camera.

## 2026.09.11.002

- Restores format, exposure, and gain separately for each camera.
- Connect opens, starts, and displays the camera; Play/Pause controls display
  updates without disconnecting it.
- Auto exposure finds the brightest non-saturating setting and warns if the
  minimum exposure still clips.
- Reference crosses support normal and 45-degree orientations, saved per
  camera.
- Numeric controls ignore mouse-wheel changes and buttons reserve enough room
  for their labels.

## 2026.09.11.001

Adds a per-camera alignment reference to Beam Profiling. After calculating a
centroid, Save centroid as reference stores that position locally with overwrite
confirmation. Show reference toggles the fixed alignment crosshair. Its colour
is selectable and defaults to green. References survive updates and camera
renaming.

## 2026.09.10.002

The former Full screen button is now Image only.
It hides the sidebar and image/acquisition control rows without changing the
window's size, position, or maximized state. Camera acquisition keeps running.
The minimum window size is reduced in this mode to support tiled camera views.
Use Show controls, F11, or Escape to restore the controls.

Existing desktop installations receive this version on their next launch after
publication. No installer rerun is needed.

## 2026.09.10.001

Initial offline Windows x64 release with per-user desktop installer,
NAS release checking, checksum verification and a local runtime cache.
