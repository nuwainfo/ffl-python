from __future__ import annotations

import zipfile
from pathlib import Path

import ffl


def test_folder_share_excludes_matching_files_from_downloaded_archive(
    tmp_path: Path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    source_directory = tmp_path / 'source-folder'
    source_directory.mkdir()
    (source_directory / 'included.txt').write_text('included', encoding='utf-8')
    (source_directory / 'ignored.txt').write_text('ignored', encoding='utf-8')
    archive = tmp_path / 'folder.zip'

    with ffl.share(
        source_directory,
        name=archive.name,
        exclude='ignored.txt',
        max_downloads=1,
        timeout_seconds=90,
    ) as session:
        result = ffl.download(session.link, output_path=archive)

    assert result.return_code == 0
    with zipfile.ZipFile(archive) as downloaded:
        assert downloaded.read('source-folder/included.txt') == b'included'
        assert 'source-folder/ignored.txt' not in downloaded.namelist()
