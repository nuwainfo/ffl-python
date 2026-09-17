from __future__ import annotations

from pathlib import Path

import ffl


def test_forced_relay_share_downloads_file(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    source = tmp_path / 'relay-source.txt'
    received = tmp_path / 'relay-received.txt'
    source.write_text('Forced relay payload', encoding='utf-8')

    with ffl.share(
        source,
        name=received.name,
        force_relay=True,
        max_downloads=1,
        timeout_seconds=90,
    ) as session:
        result = ffl.download(session.link, output_path=received)

    assert result.return_code == 0
    assert received.read_text(encoding='utf-8') == 'Forced relay payload'
    assert result.transfer_mode.name != 'UNKNOWN'
