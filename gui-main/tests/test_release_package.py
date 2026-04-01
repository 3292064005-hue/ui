from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

from robot_sim.infra.release_package import build_release_zip, iter_release_files, should_include_path


def test_should_exclude_cache_and_build_artifacts() -> None:
    assert not should_include_path(Path('__pycache__/module.cpython-310.pyc'))
    assert not should_include_path(Path('.pytest_cache/v/cache/nodeids'))
    assert not should_include_path(Path('.mypy_cache/3.10/module.meta.json'))
    assert not should_include_path(Path('.ruff_cache/0.1/index'))
    assert not should_include_path(Path('.coverage'))
    assert should_include_path(Path('src/robot_sim/core/fk.py'))


def test_iter_release_files_filters_unwanted_entries(tmp_path: Path) -> None:
    (tmp_path / 'src').mkdir()
    (tmp_path / 'src' / 'kept.py').write_text('print(1)\n', encoding='utf-8')
    (tmp_path / '.pytest_cache').mkdir()
    (tmp_path / '.pytest_cache' / 'state').write_text('x', encoding='utf-8')
    (tmp_path / '__pycache__').mkdir()
    (tmp_path / '__pycache__' / 'junk.pyc').write_bytes(b'x')
    rels = list(iter_release_files(tmp_path))
    assert rels == [Path('src/kept.py')]


def test_build_release_zip_excludes_caches(tmp_path: Path) -> None:
    (tmp_path / 'pkg').mkdir()
    (tmp_path / 'pkg' / 'real.py').write_text('x = 1\n', encoding='utf-8')
    (tmp_path / '__pycache__').mkdir()
    (tmp_path / '__pycache__' / 'junk.pyc').write_bytes(b'x')
    (tmp_path / '.coverage').write_text('data', encoding='utf-8')
    output = tmp_path / 'dist' / 'release.zip'
    build_release_zip(tmp_path, output, top_level_dir='robot_sim_engine')

    with ZipFile(output) as zf:
        names = sorted(zf.namelist())

    assert names == ['robot_sim_engine/pkg/real.py']


def test_exports_directory_is_excluded(tmp_path: Path) -> None:
    (tmp_path / 'exports').mkdir()
    (tmp_path / 'exports' / 'artifact.json').write_text('{}', encoding='utf-8')
    (tmp_path / 'src').mkdir()
    (tmp_path / 'src' / 'kept.py').write_text('print(1)\n', encoding='utf-8')
    rels = list(iter_release_files(tmp_path))
    assert rels == [Path('src/kept.py')]
