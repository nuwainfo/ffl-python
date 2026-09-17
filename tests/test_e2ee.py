from __future__ import annotations

from pathlib import Path

import ffl


def test_e2ee_share_downloads_the_original_binary_file(
    tmp_path: Path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    source = tmp_path / 'encrypted-source.bin'
    received = tmp_path / 'encrypted-received.bin'
    payload = bytes(range(256)) * 8 + b'e2ee transfer payload'
    source.write_bytes(payload)

    with ffl.share(
        source,
        name=received.name,
        e2ee=True,
        max_downloads=1,
        timeout_seconds=90,
    ) as session:
        result = ffl.download(session.link, output_path=received)

    assert result.return_code == 0
    assert received.read_bytes() == payload
    assert result.transfer_mode.name != 'UNKNOWN'
