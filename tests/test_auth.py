from __future__ import annotations

from pathlib import Path

import ffl


def test_basic_auth_share_downloads_with_matching_credentials(
    tmp_path: Path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    source = tmp_path / 'protected-source.txt'
    received = tmp_path / 'protected-received.txt'
    source.write_text('HTTP Basic Auth protected payload', encoding='utf-8')

    with ffl.share(
        source,
        name=received.name,
        auth_user='ffl-python-test',
        auth_password='correct-horse-battery-staple',
        max_downloads=1,
        timeout_seconds=90,
    ) as session:
        result = ffl.download(
            session.link,
            output_path=received,
            auth_user='ffl-python-test',
            auth_password='correct-horse-battery-staple',
        )

    assert result.return_code == 0
    assert received.read_text(encoding='utf-8') == 'HTTP Basic Auth protected payload'


def test_pickup_code_share_downloads_with_matching_code(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    source = tmp_path / 'pickup-source.txt'
    received = tmp_path / 'pickup-received.txt'
    source.write_text('Pickup code protected payload', encoding='utf-8')

    with ffl.share(
        source,
        name=received.name,
        recipient_auth='pickup',
        pickup_code='654321',
        max_downloads=1,
        timeout_seconds=90,
    ) as session:
        result = ffl.download(
            session.link,
            output_path=received,
            recipient_auth='pickup',
            pickup_code='654321',
        )

    assert result.return_code == 0
    assert received.read_text(encoding='utf-8') == 'Pickup code protected payload'
