from __future__ import annotations

from pathlib import Path

import ffl


def test_share_writes_qr_image_and_downloads_file(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    source = tmp_path / 'qr-source.txt'
    received = tmp_path / 'qr-received.txt'
    qr_image = tmp_path / 'share.png'
    source.write_text('QR share payload', encoding='utf-8')

    with ffl.share(
        source,
        name=received.name,
        qr=qr_image,
        max_downloads=1,
        timeout_seconds=90,
    ) as session:
        result = ffl.download(session.link, output_path=received)

    assert result.return_code == 0
    assert received.read_text(encoding='utf-8') == 'QR share payload'
    assert qr_image.is_file()
    assert qr_image.stat().st_size > 0
