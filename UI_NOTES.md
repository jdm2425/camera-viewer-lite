# Viewer controls

- Capture frame and Live view remain above the image while settings scroll.
- Image only hides the sidebar and image/acquisition controls while preserving
  the window size, position and maximized state. Live acquisition keeps running.
  Use Show controls, F11, or Escape to restore controls. The reduced minimum
  size allows several image-only camera windows to be tiled on one screen.
- Camera controls are disabled until a camera is opened; capture and sequence
  saving require Running. Saving a current image requires an acquired frame,
  except for screenshots.
- Saving pauses live view, locks settings, reports errors in the Saving panel,
  and restores controls afterward.
- Rename assigns a readable name to the selected camera. Names are stored
  in local Qt settings under CameraViewerLite/CameraNames, scoped by hostname.
  Blank names restore the default label. Saved camera metadata includes the name.

## Alignment reference

Enable Beam Profiling and Find centroid, then acquire an image. Save centroid as
reference stores that location for the selected camera on this PC. Replacing an
existing reference requires confirmation. Show reference toggles the saved
two-pixel-wide crosshair without affecting the moving red centroid crosshair.
Reference colour opens a colour picker and defaults to green. The location and
colour survive application updates and camera renaming.

Choose **Cross (+)** or **Diagonal (×)** beside the reference controls. The
45-degree option distinguishes the stored reference from the live centroid;
the choice is stored per camera.

## Camera operation

**Connect** opens the selected camera, restores its last format, exposure and
gain, starts its frame stream, and begins live display. **Pause/Play** stops or
resumes display updates without disconnecting the camera.

**Camera auto** restores the camera driver's fast automatic exposure and is
the recommended routine option. It can be toggled off to return to manual
exposure. **Safe exposure scan** remains available as an optional, slower
one-shot search for the brightest setting below clipping. If the minimum
exposure is still saturated, the viewer asks for a lower light level or
additional attenuation. Numeric controls ignore mouse-wheel changes.

## Camera identity limitation

The existing OpenCV DirectShow wrapper supplies numeric camera indices, not
stable hardware identifiers. Aliases therefore refer to camera numbers on this
PC. Check names after plugging/unplugging or reordering cameras. Do not assume
aliases follow physical devices. A future device-enumeration integration is
needed for names that reliably follow a camera across USB ports.

## Verification

With the lab2 environment activated, run:

    python -m unittest discover -s tests -p test_viewer_ui.py

These tests use an offscreen UI and mocks; they do not open cameras.
Live acquisition and hardware-specific controls still require a camera check.

Published desktop installations receive tested releases through the NAS updater.
