from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path


def test_ape_is_tracked_as_an_executable_file():
    completed = subprocess.run(
        ['git', 'ls-files', '-s', 'src/ffl/bin/ffl.com'],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout.startswith('100755 ')


def test_wheel_contains_type_marker_and_executable_ape(tmp_path: Path):
    wheel_directory = tmp_path / 'wheel'
    subprocess.run(
        [
            sys.executable,
            '-m',
            'build',
            '--wheel',
            '--outdir',
            str(wheel_directory),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    wheel_path = next(wheel_directory.glob('*.whl'))

    with zipfile.ZipFile(wheel_path) as archive:
        assert 'ffl/py.typed' in archive.namelist()
        mode = archive.getinfo('ffl/bin/ffl.com').external_attr >> 16
        assert mode & 0o111
