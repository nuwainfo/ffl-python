from __future__ import annotations

import zipfile
from pathlib import Path

import ffl


def _download_shared_file(
    source: str | Path | list[Path],
    received: Path,
    *,
    name: str | None = None,
) -> ffl.DownloadResult:
    with ffl.share(
        source,
        name=name or received.name,
        max_downloads=1,
        timeout_seconds=90,
    ) as session:
        result = ffl.download(session.link, output_path=received)

    assert result.return_code == 0
    assert result.transfer_mode.name != 'UNKNOWN'
    assert received.is_file()
    return result


def test_version_and_raw_access_report_bundled_ffl_version():
    assert 'FastFileLink' in ffl.version()

    result = ffl.raw(['download', '--version'])

    assert result.return_code == 0
    assert 'FastFileLink' in result.stdout


def test_share_and_download_a_binary_file(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    source = tmp_path / 'source.bin'
    received = tmp_path / 'received.bin'
    payload = bytes(range(256)) * 16 + b'ffl-python end-to-end transfer'
    source.write_bytes(payload)

    _download_shared_file(source, received)

    assert received.read_bytes() == payload


def test_share_text_and_download_preserves_utf8_and_cleans_up(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    received = tmp_path / 'message.txt'
    text = 'FFL Python: 你好，portable APE.\n'

    with ffl.share_text(text, name=received.name) as session:
        result = ffl.download(session.link, output_path=received)

    assert result.return_code == 0
    assert received.read_text(encoding='utf-8') == text
    assert not tuple(tmp_path.glob('ffl-python-*'))


def test_share_bytes_and_download_preserves_binary_content(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    received = tmp_path / 'payload.dat'
    payload = b'\x00\xff\x10ffl-python\x00' * 128

    with ffl.share_bytes(payload, name=received.name) as session:
        result = ffl.download(session.link, output_path=received)

    assert result.return_code == 0
    assert received.read_bytes() == payload
    assert not tuple(tmp_path.glob('ffl-python-*'))


def test_download_stream_preserves_binary_content(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    source = tmp_path / 'stream-source.bin'
    payload = bytes(range(256)) * 4096
    source.write_bytes(payload)

    with ffl.share(source, max_downloads=1, timeout_seconds=90) as session:
        transfer = ffl.download_stream(session.link)
        received = b''.join(transfer.iter_bytes())
        result = transfer.wait()

    assert result.return_code == 0
    assert result.process.stdout == ''
    assert received == payload, received[:1000].decode('utf-8', errors='replace')


def test_share_multiple_files_downloads_named_archive(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    first = tmp_path / 'first.txt'
    second = tmp_path / 'second.txt'
    archive = tmp_path / 'bundle.zip'
    first.write_text('first file', encoding='utf-8')
    second.write_text('second file', encoding='utf-8')

    _download_shared_file([first, second], archive, name=archive.name)

    with zipfile.ZipFile(archive) as downloaded:
        assert downloaded.read(first.name) == b'first file'
        assert downloaded.read(second.name) == b'second file'


def test_keygen_creates_the_reported_key_pair(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = ffl.keygen('pytest-recipient')

    assert result.return_code == 0
    assert result.private_key_path == tmp_path / 'pytest-recipient.fflkey'
    assert result.public_key_path == tmp_path / 'pytest-recipient.fflpub'
    assert result.private_key_path.read_text(encoding='utf-8')
    assert result.public_key_path.read_text(encoding='utf-8')
