# Validation — 2026-10-31

- Python 3.11 on macOS ARM64.
- `python -m pytest -q`: 30 tests passed after independent review fixes.
- `python -m compileall -q video_folder.py __init__.py`: passed.
- Tests cover real filesystem selection, natural/modified ordering, recursive
  scans, explicit picks, batch boundaries, filenames, skip_done, file changes,
  quoted paths/spaces, relative ComfyUI input paths, and symlink containment.
- ComfyUI factory boundary is substituted with a small class in two tests.
  Real selection and returned list alignment execute; this is not a claim of
  native video decoding or audio/video encoding test coverage.
- Workflow JSON links, slots, input types, filename wiring and audio/FPS routing
  checked. Native node schema/API inspected against current ComfyUI source.
- Package import uses only Python standard library until node execution.

Limits: no live ComfyUI server/frontend is installed here, so import/queue in
ComfyUI and playback of saved output remain unverified. Video codec support and
frame/audio decoding are provided by ComfyUI. CI is configured for Python 3.10
and 3.12 on Windows/Linux; remote results are separate from these local checks.

Independent review identified repeated output-directory scanning and filename
case conflation. Three regression tests failed before the fixes, then passed:
each output directory is now indexed once, extension case is preserved, and
completion matching follows platform case normalization.

## Direct IMAGE outputs — 2026-11-01

Appended IMAGE/AUDIO/FLOAT ports without shifting the original six outputs.
Native get_components supplies frame batches, optional audio and fractional FPS.
Regression tests failed before implementation and pass afterward; full suite
now 32 passed. Both example workflows updated and their links checked.
The loader now decodes every selected file eagerly; README documents RAM use.
Native ComfyUI decode/encode and live frontend execution remain unverified here.
