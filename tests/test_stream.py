from __future__ import annotations

from io import BytesIO

from ffl import client as client_module


def test_share_stream_passes_binary_source_to_generated_runtime(monkeypatch):
    captured = {}
    source = BytesIO(b'backup-data')

    def share(**values):
        captured.update(values)
        return object()

    monkeypatch.setattr(client_module._generated, 'share', share)
    monkeypatch.setattr(client_module, 'ShareSession', lambda session, **_kwargs: session)

    result = client_module.FFLClient().share_stream(source, name='backup.sql')

    assert result is not None
    assert captured['paths'] == '-'
    assert captured['name'] == 'backup.sql'
    assert captured['stdin'] is source
    assert captured['stdin_cache'] == 'off'
