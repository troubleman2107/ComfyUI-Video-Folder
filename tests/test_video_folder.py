import importlib.util
from pathlib import Path
import os
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from video_folder import LoadVideosFromFolder, select_videos


def put(root, *names):
    for name in names:
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b'test source')


def selected(root, **kwargs):
    return select_videos(str(root), **kwargs)


def names(selection):
    return [e.relative for e in selection.entries]


def test_natural_sort_extensions_and_nonvideo_filter(tmp_path):
    put(tmp_path, 'clip10.mp4', 'clip2.MOV', 'clip1.webm', 'image.png', 'README.txt')
    result = selected(tmp_path, batch_size=0)
    assert names(result) == ['clip1.webm', 'clip2.MOV', 'clip10.mp4']
    assert result.available == 3 and result.start_index == 0


def test_batch_slice_and_default_one_video(tmp_path):
    put(tmp_path, '1.mp4', '2.mp4', '3.mp4', '4.mp4')
    assert names(selected(tmp_path)) == ['1.mp4']
    result = selected(tmp_path, start_index=1, batch_size=2)
    assert names(result) == ['2.mp4', '3.mp4'] and result.available == 4
    assert names(selected(tmp_path, start_index=2, batch_size=0)) == ['3.mp4', '4.mp4']
    with pytest.raises(ValueError, match='start_index'):
        selected(tmp_path, start_index=4)


def test_recursive_selection_and_explicit_file_order(tmp_path):
    put(tmp_path, 'a.mp4', 'sub/b.mp4', 'sub/c.mp4')
    assert names(selected(tmp_path, batch_size=0)) == ['a.mp4']
    assert names(selected(tmp_path, recursive=True, batch_size=0)) == ['a.mp4', 'sub/b.mp4', 'sub/c.mp4']
    result = selected(tmp_path, recursive=True, selected_files='sub\\c.mp4\n\na.mp4\nsub/c.mp4', batch_size=0)
    assert names(result) == ['sub/c.mp4', 'a.mp4']
    with pytest.raises(ValueError, match='not found'):
        selected(tmp_path, selected_files='missing.mp4')


def test_modified_time_and_reverse_sort(tmp_path):
    put(tmp_path, 'a.mp4', 'b.mp4')
    os.utime(tmp_path / 'a.mp4', (200, 200))
    os.utime(tmp_path / 'b.mp4', (100, 100))
    assert names(selected(tmp_path, sort_by='modified', batch_size=0)) == ['b.mp4', 'a.mp4']
    assert names(selected(tmp_path, sort_by='modified', descending=True, batch_size=0)) == ['a.mp4', 'b.mp4']


def test_output_names_are_unique_across_extensions_and_folders(tmp_path):
    put(tmp_path, 'clip.mp4', 'clip.mov', 'sub/clip.mp4')
    result = selected(tmp_path, recursive=True, batch_size=0)
    prefixes = [e.filename for e in result.entries]
    assert len(set(prefixes)) == 3
    assert 'clip__mp4' in prefixes and 'sub/clip__mp4' in prefixes
    assert not any('..' in Path(p).parts for p in prefixes)


def test_skip_done_matches_only_save_video_outputs_and_filters_before_slice(tmp_path):
    source, done = tmp_path / 'source', tmp_path / 'done'
    put(source, '1.mp4', '2.mp4', '3.mp4')
    put(done, '1__mp4_00001_.mp4', '2__mp4.txt', '3__mp4_extra.mp4')
    result = selected(source, skip_done=True, output_folder=str(done), batch_size=1)
    assert names(result) == ['2.mp4'] and result.available == 2
    put(done, '2__mp4_00002_.mkv', '3__mp4_00003_.mp4')
    with pytest.raises(ValueError, match='already processed'):
        selected(source, skip_done=True, output_folder=str(done))


def test_skip_done_never_counts_source_file_itself(tmp_path):
    put(tmp_path, '1.mp4', '1__mp4_00001_.mp4')
    result = selected(tmp_path, skip_done=True, output_folder=str(tmp_path), batch_size=0)
    assert len(result.entries) == 2


def test_recursive_skip_done_and_missing_output_folder(tmp_path):
    source, done = tmp_path / 'source', tmp_path / 'done'
    put(source, 'sub/one.mp4', 'sub/two.mp4')
    result = selected(source, recursive=True, skip_done=True, output_folder=str(done), batch_size=0)
    assert len(result.entries) == 2
    put(done, 'sub/one__mp4_00001_.mp4')
    assert names(selected(source, recursive=True, skip_done=True, output_folder=str(done))) == ['sub/two.mp4']


@pytest.mark.parametrize('kwargs', [
    {'start_index': -1}, {'batch_size': -1}, {'sort_by': 'random'},
    {'skip_done': True, 'output_folder': ''},
    {'selected_files': '../escape.mp4'}, {'selected_files': 'C:\\secret.mp4'},
    {'selected_files': '/secret.mp4'},
])
def test_invalid_options_rejected(tmp_path, kwargs):
    put(tmp_path, 'a.mp4')
    with pytest.raises(ValueError):
        selected(tmp_path, **kwargs)


@pytest.mark.parametrize('folder', ['', '//server/share', '\\\\server\\share', 'https://example.com/videos'])
def test_invalid_folder_rejected_before_filesystem_access(folder):
    with pytest.raises(ValueError):
        select_videos(folder)


def test_empty_and_missing_folder(tmp_path):
    with pytest.raises(ValueError, match='No video'):
        selected(tmp_path)
    with pytest.raises(ValueError, match='not found'):
        selected(tmp_path / 'missing')


def test_symlink_escape_is_excluded(tmp_path):
    source = tmp_path / 'source'
    put(source, 'inside.mp4')
    put(tmp_path, 'outside.mp4')
    try:
        (source / 'escape.mp4').symlink_to(tmp_path / 'outside.mp4')
        (source / 'loop').symlink_to(source, target_is_directory=True)
    except OSError:
        pytest.skip('Symlinks not supported by this test account')
    assert names(selected(source, recursive=True, batch_size=0)) == ['inside.mp4']


def test_cache_tracks_files_and_done_outputs(tmp_path):
    source, done = tmp_path / 'source', tmp_path / 'done'
    put(source, '1.mp4', '2.mp4')
    args = dict(folder=str(source), batch_size=0, skip_done=True, output_folder=str(done))
    a = LoadVideosFromFolder.IS_CHANGED(**args)
    (source / '1.mp4').write_bytes(b'changed content')
    b = LoadVideosFromFolder.IS_CHANGED(**args)
    put(done, '1__mp4_00001_.mp4')
    c = LoadVideosFromFolder.IS_CHANGED(**args)
    assert len({a,b,c}) == 3


def test_native_video_boundary_and_output_lists_align(tmp_path, monkeypatch):
    # Only substitute the external ComfyUI factory; test real scanning and mapping.
    import video_folder
    opened = []
    class Video:
        def __init__(self, path):
            assert Path(path).is_absolute() and Path(path).is_file()
            self.path = path
            opened.append(path)
        def get_dimensions(self):
            return 64, 48
    monkeypatch.setattr(video_folder, '_video_class', lambda: Video)
    put(tmp_path, 'clip1.mp4', 'clip2.mp4')
    result = LoadVideosFromFolder().load(str(tmp_path), batch_size=0)
    videos, filenames, paths, indices, totals, available = result
    assert [v.path for v in videos] == paths == opened
    assert filenames == ['clip1__mp4', 'clip2__mp4']
    assert indices == [1,2] and totals == [2,2] and available == [2,2]
    assert all(LoadVideosFromFolder.OUTPUT_IS_LIST)
    assert len(result) == len(LoadVideosFromFolder.RETURN_TYPES)


def test_unreadable_video_reports_filename(tmp_path, monkeypatch):
    import video_folder
    class BadVideo:
        def __init__(self, path): pass
        def get_dimensions(self): raise RuntimeError('invalid codec')
    monkeypatch.setattr(video_folder, '_video_class', lambda: BadVideo)
    put(tmp_path, 'broken.mp4')
    with pytest.raises(ValueError, match='broken.mp4'):
        LoadVideosFromFolder().load(str(tmp_path))


def test_folder_with_quotes_and_spaces(tmp_path):
    folder = tmp_path / 'video collection'
    put(folder, 'Tiếng Việt.mp4')
    assert names(select_videos('"' + str(folder) + '"')) == ['Tiếng Việt.mp4']


def test_relative_folder_is_under_comfy_input(tmp_path, monkeypatch):
    from types import SimpleNamespace
    put(tmp_path, 'clips/1.mp4')
    monkeypatch.setitem(sys.modules, 'folder_paths', SimpleNamespace(get_input_directory=lambda: str(tmp_path)))
    assert names(select_videos('clips')) == ['1.mp4']


def test_package_registration_and_workflow_links():
    import json
    import __init__ as package
    cls = package.NODE_CLASS_MAPPINGS['TM_LoadVideosFromFolder']
    assert cls.RETURN_TYPES[0] == 'VIDEO'
    for path in (ROOT / 'examples').glob('*.json'):
        data = json.loads(path.read_text())
        nodes = {n['id']: n for n in data['nodes']}
        for lid, src, src_slot, dst, dst_slot, kind in data['links']:
            assert lid in nodes[src]['outputs'][src_slot]['links']
            assert nodes[dst]['inputs'][dst_slot]['link'] == lid
            assert nodes[src]['outputs'][src_slot]['type'] == kind
            assert nodes[dst]['inputs'][dst_slot]['type'] == kind
        source = next(n for n in nodes.values() if n['type'] == 'TM_LoadVideosFromFolder')
        assert len(source['widgets_values']) == len(cls.INPUT_TYPES()['required'])
        sink = next(n for n in nodes.values() if n['type'] == 'SaveVideo')
        name_input = next(i for i in sink['inputs'] if i['name'] == 'filename_prefix')
        name_link = next(l for l in data['links'] if l[0] == name_input['link'])
        assert name_link[1:3] == [source['id'], 1]
        if 'watermark' in path.name:
            create = next(n for n in nodes.values() if n['type'] == 'CreateVideo')
            for input_name, slot in [('audio',1),('fps',2)]:
                inlet = next(i for i in create['inputs'] if i['name'] == input_name)
                link = next(l for l in data['links'] if l[0] == inlet['link'])
                assert nodes[link[1]]['type'] == 'GetVideoComponents' and link[2] == slot


def test_skip_done_reads_each_output_directory_once(tmp_path, monkeypatch):
    source, done = tmp_path / 'source', tmp_path / 'done'
    put(source, *(f'clip{i}.mp4' for i in range(40)))
    put(done, *(f'unrelated{i}.mp4' for i in range(40)))
    original = Path.iterdir
    scans = []
    def measured(path):
        if path == done:
            scans.append(path)
        return original(path)
    monkeypatch.setattr(Path, 'iterdir', measured)
    assert len(selected(source, skip_done=True, output_folder=str(done)).entries) == 1
    assert len(scans) == 1


def test_source_extension_case_is_preserved_in_prefix(tmp_path):
    put(tmp_path, 'clip.MP4')
    assert selected(tmp_path).entries[0].filename == 'clip__MP4'


@pytest.mark.skipif(os.name == 'nt', reason='Windows matching is intentionally case insensitive')
def test_skip_done_does_not_conflate_case_sensitive_prefixes(tmp_path):
    source, done = tmp_path / 'source', tmp_path / 'done'
    put(source, 'clip.mp4')
    put(done, 'Clip__mp4_00001_.mp4')
    assert names(selected(source, skip_done=True, output_folder=str(done))) == ['clip.mp4']
