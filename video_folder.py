"""Independent folder batching for ComfyUI's native VIDEO type."""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re

VIDEO_EXTENSIONS = frozenset({'.mp4', '.mov', '.mkv', '.webm', '.avi', '.m4v', '.mpeg', '.mpg', '.ts', '.mts', '.m2ts', '.wmv', '.flv'})
MAX_SCAN_FILES = 100000


@dataclass(frozen=True)
class VideoEntry:
    path: Path
    relative: str
    filename: str


@dataclass(frozen=True)
class Selection:
    entries: list[VideoEntry]
    available: int
    start_index: int


def _local_folder(value, *, allow_missing=False):
    if not isinstance(value, str):
        raise ValueError('Folder must be a local filesystem path.')
    raw = value.strip()
    if len(raw) > 1 and raw[0] == raw[-1] == '"':
        raw = raw[1:-1]
    if not raw:
        raise ValueError('Enter a folder path on the computer running ComfyUI.')
    # Reject remote paths before resolve/stat, including Windows UNC/device paths.
    if raw.startswith(('\\\\', '//')) or re.match(r'^[a-zA-Z][\w+.-]*://', raw):
        raise ValueError('Use a local folder, not a URL or UNC/network path.')
    path = Path(raw).expanduser()
    if not path.is_absolute():
        if PureWindowsPath(raw).drive or raw.startswith('\\'):
            raise ValueError('Use an absolute local path valid on this server.')
        try:
            import folder_paths
            path = Path(folder_paths.get_input_directory()) / path
        except ImportError as exc:
            raise ValueError('Use an absolute folder path; relative paths require ComfyUI.') from exc
    path = path.resolve()
    if not path.is_dir() and not (allow_missing and not path.exists()):
        raise ValueError(f'Folder not found or not a directory: {path}')
    return path


def _natural(text):
    return tuple((1, int(part)) if part.isdigit() else (0, part.casefold())
                 for part in re.split(r'(\d+)', text))


def _prefix(relative):
    path = Path(relative)
    raw_parts = list(path.parent.parts) + [path.stem + '__' + path.suffix[1:]]
    clean_parts = []
    changed = False
    for part in raw_parts:
        clean = re.sub(r'[<>:"\\|?*%\x00-\x1f]', '_', part).rstrip(' .') or '_'
        if re.fullmatch(r'(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])', clean):
            clean = '_' + clean
        changed |= clean != part
        clean_parts.append(clean)
    if changed:
        clean_parts[-1] += '_' + hashlib.sha256(relative.encode()).hexdigest()[:10]
    return '/'.join(clean_parts)


def _scan(folder, recursive):
    entries = []
    visited = 0

    def onerror(error):
        raise ValueError(f'Cannot read folder: {error.filename}: {error.strerror}') from error

    for root, dirs, files in os.walk(folder, followlinks=False, onerror=onerror):
        dirs[:] = sorted(d for d in dirs if not (Path(root) / d).is_symlink()) if recursive else []
        for name in files:
            visited += 1
            if visited > MAX_SCAN_FILES:
                raise ValueError(f'Too many files (over {MAX_SCAN_FILES}). Choose a smaller folder.')
            lexical = Path(root) / name
            if lexical.suffix.lower() not in VIDEO_EXTENSIONS:
                continue
            path = lexical.resolve()
            if not path.is_relative_to(folder) or not path.is_file():
                continue
            relative = lexical.relative_to(folder).as_posix()
            entries.append(VideoEntry(path, relative, _prefix(relative)))
    return entries


def _done_prefixes(entries, output, source_paths):
    """Index each relevant output directory once, even for large source batches."""
    completed = set()
    visited = 0
    parents = {Path(entry.filename).parent for entry in entries}
    for relative_parent in sorted(parents):
        parent = (output / relative_parent).resolve()
        if not parent.is_relative_to(output) or not parent.is_dir():
            continue
        try:
            for result in parent.iterdir():
                visited += 1
                if visited > MAX_SCAN_FILES:
                    raise ValueError(f'Too many output files (over {MAX_SCAN_FILES}). Choose a smaller output folder.')
                if result.suffix.lower() not in VIDEO_EXTENSIONS:
                    continue
                resolved = result.resolve()
                if (not resolved.is_relative_to(output) or resolved in source_paths
                        or not result.is_file() or result.stat().st_size == 0):
                    continue
                # Accept exact prefix.ext and ComfyUI's prefix_00001_.ext.
                for stem in {result.stem, re.sub(r'_\d+_$', '', result.stem)}:
                    name = (relative_parent / stem).as_posix()
                    completed.add(os.path.normcase(name))
        except OSError as exc:
            raise ValueError(f'Cannot inspect output folder: {parent}') from exc
    return completed


def select_videos(folder, recursive=False, sort_by='name', descending=False,
                  start_index=0, batch_size=1, selected_files='', skip_done=False,
                  output_folder=''):
    """Filter/pick/sort, remove completed files, then slice a batch (0 = all)."""
    for key, value in [('start_index', start_index), ('batch_size', batch_size)]:
        if type(value) is not int or not 0 <= value <= MAX_SCAN_FILES:
            raise ValueError(f'{key} must be an integer between 0 and {MAX_SCAN_FILES}.')
    if sort_by not in ('name', 'modified'):
        raise ValueError('sort_by must be name or modified.')
    if not isinstance(selected_files, str):
        raise ValueError('selected_files must contain one relative filename per line.')
    root = _local_folder(folder)
    all_entries = _scan(root, recursive)
    if not all_entries:
        raise ValueError(f'No video files found in {root}. Check recursive and file extensions.')
    source_paths = {e.path for e in all_entries}
    if selected_files.strip():
        by_name = {e.relative: e for e in all_entries}
        entries, seen = [], set()
        for line in selected_files.splitlines():
            relative = line.strip().replace('\\', '/')
            if not relative:
                continue
            if relative.startswith('/') or PureWindowsPath(relative).drive or '..' in Path(relative).parts:
                raise ValueError('Selected filenames must be relative paths inside the folder.')
            if relative not in by_name:
                raise ValueError(f'Selected video not found: {relative}. Enable recursive for subfolders.')
            if relative not in seen:
                entries.append(by_name[relative])
                seen.add(relative)
    else:
        def sort_key(entry):
            tie = (_natural(entry.relative), entry.relative)
            return (entry.path.stat().st_mtime_ns, tie) if sort_by == 'modified' else tie
        entries = sorted(all_entries, key=sort_key, reverse=descending)
    if skip_done:
        output = _local_folder(output_folder, allow_missing=True)
        completed = _done_prefixes(entries, output, source_paths)
        entries = [e for e in entries if os.path.normcase(e.filename) not in completed]
        if not entries:
            raise ValueError('All selected videos are already processed. Disable skip_done to run again.')
    available = len(entries)
    if start_index >= available:
        raise ValueError(f'start_index={start_index} is outside {available} available videos. Reset it to 0.')
    end = start_index + batch_size if batch_size else available
    return Selection(entries[start_index:end], available, start_index)


def _video_class():
    try:
        from comfy_api.input_impl import VideoFromFile
        return VideoFromFile
    except ImportError:
        try:
            from comfy_api.latest import InputImpl
            return InputImpl.VideoFromFile
        except (ImportError, AttributeError) as exc:
            raise RuntimeError('Native VIDEO API unavailable. Update ComfyUI to a version with Load Video, Get Video Components and Create Video, then restart. No NumPy or PyTorch upgrade is required by this custom node.') from exc


class LoadVideosFromFolder:
    CATEGORY = 'video/batch'
    FUNCTION = 'load'
    RETURN_TYPES = ('VIDEO', 'STRING', 'STRING', 'INT', 'INT', 'INT')
    RETURN_NAMES = ('video', 'filename', 'path', 'index', 'total', 'available')
    OUTPUT_IS_LIST = (True,) * 6
    DESCRIPTION = ('Load separate video files as a ComfyUI list, preserving native audio/FPS. '
                   'batch_size counts FILES, not frames; 0 loads all remaining files. '
                   'Keep Queue batch count at 1. Start with batch_size=1 for large videos.')

    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {
            'folder': ('STRING', {'default': '', 'tooltip': 'Local folder on the ComfyUI server. Relative paths are under ComfyUI/input.'}),
            'recursive': ('BOOLEAN', {'default': False}),
            'sort_by': (['name', 'modified'],),
            'descending': ('BOOLEAN', {'default': False}),
            'start_index': ('INT', {'default': 0, 'min': 0, 'max': MAX_SCAN_FILES}),
            'batch_size': ('INT', {'default': 1, 'min': 0, 'max': MAX_SCAN_FILES, 'tooltip': 'Number of video files in this run; 0 = all remaining.'}),
            'selected_files': ('STRING', {'default': '', 'multiline': True, 'tooltip': 'Optional relative names, one per line, in processing order. Empty selects all.'}),
            'skip_done': ('BOOLEAN', {'default': False}),
            'output_folder': ('STRING', {'default': '', 'tooltip': 'Absolute path to the output folder used by Save Video. Only used with skip_done.'}),
        }}

    def load(self, folder, recursive=False, sort_by='name', descending=False,
             start_index=0, batch_size=1, selected_files='', skip_done=False,
             output_folder=''):
        selection = select_videos(folder, recursive, sort_by, descending,
                                  start_index, batch_size, selected_files, skip_done, output_folder)
        video_type = _video_class()
        videos = []
        for entry in selection.entries:
            try:
                video = video_type(str(entry.path))
                width, height = video.get_dimensions()
                if width < 1 or height < 1:
                    raise ValueError('Video has no valid dimensions.')
            except Exception as exc:
                raise ValueError(f'Cannot open video {entry.relative!r}: {exc}') from exc
            videos.append(video)
        count = len(videos)
        return (videos, [e.filename for e in selection.entries],
                [str(e.path) for e in selection.entries],
                list(range(start_index + 1, start_index + count + 1)),
                [count] * count, [selection.available] * count)

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        try:
            selection = select_videos(**kwargs)
            state = [(e.relative, str(e.path), e.path.stat().st_size, e.path.stat().st_mtime_ns)
                     for e in selection.entries]
            payload = (kwargs, selection.available, state)
            return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        except (ValueError, OSError):
            return float('nan')
