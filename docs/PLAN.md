# Load Videos from Folder implementation

User wants a video equivalent of Pixaroma's image folder batch node, packaged
in an independent repository. User previously authorized direct implementation.

Design: a standard ComfyUI node with visible folder, recursive, sort, direction,
start_index, batch_size and optional selected_files inputs. It emits lists of
native VIDEO objects, safe filename prefixes, full paths, 1-based index within
selection, total selected count and total available. An optional skip_done plus
output_folder filters already saved results before slicing. No gallery clone:
selection uses newline-separated relative names, no web extension or HTTP route.
Use natural name ordering; preserve each source extension in output prefix to
avoid foo.mp4 and foo.mov collisions. Include relative subfolder paths in prefix.
Video objects are lazy references; downstream list processing can still retain
multiple decoded videos, so default batch_size=1. Zero means all remaining.
Never concatenate unrelated video frames. Audio/FPS stay inside native VIDEO.

No new runtime dependency installation. Use ComfyUI's native VideoFromFile via
lazy import so older ComfyUI gets a useful update message when executing. Require
local filesystem folders, reject network URI/UNC paths and file symlink escapes.
Unreadable video detected by checking native get_dimensions; fail with filename.
No silent omission of failed files. Keep watermark package untouched.

Tasks:
1. Write failing file selection tests: filters, natural sort, batch boundaries,
   recursive traversal, explicit picks, invalid inputs, safe output names,
   skip_done semantics, symlink containment, changed files invalidate cache.
2. Implement selection in video_folder.py and native VIDEO list registration.
   Test list alignment with narrow core API boundary substitute where ComfyUI
   isn't installed. Document this limit rather than claiming real decode tests.
3. Supply standalone passthrough and watermark integration UI workflow JSON,
   Vietnamese README, dependency-free installation, CI and ZIP.
4. Run suite, inspect workflow links, independent code review, address findings.
5. Create standalone GitHub repo and push, then verify remote revision.

Review focus: same filenames across folders/extensions; Windows drive paths and
input-relative paths; failed codec handling; skip_done output detection must not
count source video as its own output; list lengths always match; cache reruns
when folder content or output markers change.
