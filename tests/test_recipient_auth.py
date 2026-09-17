from __future__ import annotations

from pathlib import Path

import ffl


def test_public_key_recipient_auth_share_downloads_with_private_key(
    tmp_path: Path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    key_pair = ffl.keygen('recipient')
    source = tmp_path / 'recipient-source.txt'
    received = tmp_path / 'recipient-received.txt'
    source.write_text('Public key protected payload', encoding='utf-8')

    with ffl.share(
        source,
        name=received.name,
        recipient_auth='pubkey',
        recipient_public_key=key_pair.public_key_path,
        max_downloads=1,
        timeout_seconds=90,
    ) as session:
        result = ffl.download(
            session.link,
            output_path=received,
            recipient_auth='pubkey',
            recipient_private_key=key_pair.private_key_path,
        )

    assert result.return_code == 0
    assert received.read_text(encoding='utf-8') == 'Public key protected payload'
