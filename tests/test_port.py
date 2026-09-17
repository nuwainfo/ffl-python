from __future__ import annotations

import socket
from pathlib import Path

import ffl


def _available_port() -> int:
    with socket.socket() as socket_handle:
        socket_handle.bind(('127.0.0.1', 0))
        return socket_handle.getsockname()[1]


def test_share_uses_requested_port_and_downloads_file(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    source = tmp_path / 'port-source.txt'
    received = tmp_path / 'port-received.txt'
    source.write_text('Explicit port payload', encoding='utf-8')

    with ffl.share(
        source,
        name=received.name,
        port=_available_port(),
        max_downloads=1,
        timeout_seconds=90,
    ) as session:
        result = ffl.download(session.link, output_path=received)

    assert result.return_code == 0
    assert received.read_text(encoding='utf-8') == 'Explicit port payload'
