from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import ffl


class _HookHandler(BaseHTTPRequestHandler):
    requests: list[tuple[str, bytes]] = []
    received_event = threading.Event()

    def do_POST(self) -> None:
        content_length = int(self.headers.get('Content-Length', '0'))
        self.__class__.requests.append((self.path, self.rfile.read(content_length)))
        self.__class__.received_event.set()
        self.send_response(204)
        self.end_headers()

    def log_message(self, format_string: str, *args) -> None:
        del format_string, args


def test_share_sends_events_to_hook_url(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _HookHandler.requests = []
    _HookHandler.received_event.clear()
    server = ThreadingHTTPServer(('127.0.0.1', 0), _HookHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    source = tmp_path / 'hook-source.txt'
    received = tmp_path / 'hook-received.txt'
    source.write_text('Hook payload', encoding='utf-8')

    try:
        hook_url = f'http://127.0.0.1:{server.server_port}/events'
        with ffl.share(
            source,
            name=received.name,
            hook_url=hook_url,
            max_downloads=1,
            timeout_seconds=90,
        ) as session:
            result = ffl.download(session.link, output_path=received)
            assert session.event_history
            endpoint_events = [
                event
                for event in session.event_history
                if event.name == '/hook/server/endpoints/register'
            ]
            assert endpoint_events
            replayed = []
            session.on_raw('/hook/server/endpoints/register', replayed.append)
            assert replayed == endpoint_events
            event = next(session.events())
            assert event.name.startswith('/')

        assert result.return_code == 0
        assert received.read_text(encoding='utf-8') == 'Hook payload'
        assert _HookHandler.received_event.wait(timeout=5)
        assert any(path == '/events' and body for path, body in _HookHandler.requests)
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=5)


def test_share_can_defer_hook_event_handling_to_the_caller(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _HookHandler.requests = []
    _HookHandler.received_event.clear()
    server = ThreadingHTTPServer(('127.0.0.1', 0), _HookHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    source = tmp_path / 'direct-hook-source.txt'
    received = tmp_path / 'direct-hook-received.txt'
    source.write_text('Direct hook payload', encoding='utf-8')

    try:
        hook_url = f'http://127.0.0.1:{server.server_port}/events'
        with ffl.share(
            source,
            name=received.name,
            hook_url=hook_url,
            capture_hook_events=False,
            max_downloads=1,
            timeout_seconds=90,
        ) as session:
            result = ffl.download(session.link, output_path=received)
            assert session.event_history == ()

        assert result.return_code == 0
        assert received.read_text(encoding='utf-8') == 'Direct hook payload'
        assert _HookHandler.received_event.wait(timeout=5)
        assert any(path == '/events' and body for path, body in _HookHandler.requests)
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=5)
