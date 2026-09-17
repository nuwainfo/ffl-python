from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import Request, urlopen

import pytest

from ffl.events import FFLHookEventChannel


def _event_body(index: int, name: str = '/hook/transfer/progress') -> bytes:
    return json.dumps({'event': name, 'data': {'index': index}}).encode('utf-8')


def test_hook_history_is_bounded_and_exposes_semantic_event_names():
    channel = FFLHookEventChannel(event_history_limit=2)
    try:
        channel._publish(_event_body(1))
        channel._publish(_event_body(2))
        channel._publish(_event_body(3, '/hook/transfer/complete'))

        assert [event.data['index'] for event in channel.history] == [2, 3]
        assert channel.history[-1].semantic_name == 'completed'
        replayed = []
        replayed_event = threading.Event()
        channel.on_semantic(
            'completed',
            lambda event: (replayed.append(event), replayed_event.set()),
        )
        assert replayed_event.wait(timeout=1)
        assert replayed == [channel.history[-1]]
    finally:
        channel.close()


def test_live_event_iterator_preserves_events_after_history_eviction():
    channel = FFLHookEventChannel(event_history_limit=2)
    iterator = channel.events()
    try:
        channel._publish(_event_body(1))
        assert next(iterator).data['index'] == 1
        channel._publish(_event_body(2))
        channel._publish(_event_body(3))
        channel._publish(_event_body(4))

        assert [event.data['index'] for event in channel.history] == [3, 4]
        assert next(iterator).data['index'] == 2
        assert next(iterator).data['index'] == 3
        assert next(iterator).data['index'] == 4
    finally:
        iterator.close()
        channel.close()


@pytest.mark.parametrize('limit', [0, -1, True, '100'])
def test_hook_history_limit_requires_a_positive_integer(limit):
    with pytest.raises((TypeError, ValueError)):
        FFLHookEventChannel(event_history_limit=limit)


def test_hook_response_does_not_wait_for_forwarded_webhook():
    forwarded = threading.Event()
    release_forward = threading.Event()

    class SlowHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            forwarded.set()
            release_forward.wait(timeout=5)
            self.send_response(204)
            self.end_headers()

        def log_message(self, format_string: str, *args) -> None:
            del format_string, args

    server = ThreadingHTTPServer(('127.0.0.1', 0), SlowHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    channel = FFLHookEventChannel(f'http://127.0.0.1:{server.server_port}/events')

    try:
        started = time.monotonic()
        request = Request(channel.url, data=_event_body(1), method='POST')
        with urlopen(request, timeout=1) as response:
            assert response.status == 204

        assert time.monotonic() - started < 0.5
        assert forwarded.wait(timeout=1)
    finally:
        release_forward.set()
        channel.close()
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=5)


def test_hook_forwarding_suppresses_direct_timeout_errors(monkeypatch):
    channel = FFLHookEventChannel('http://127.0.0.1:1/events')

    def raise_timeout(*_args, **_kwargs):
        raise TimeoutError('timed out')

    monkeypatch.setattr('ffl.events.urlopen', raise_timeout)
    try:
        channel._forward(_event_body(1))
    finally:
        channel.close()


def test_hook_response_does_not_wait_for_a_local_listener():
    listener_started = threading.Event()
    release_listener = threading.Event()
    channel = FFLHookEventChannel()
    channel.on(
        '/hook/transfer/progress',
        lambda event: (listener_started.set(), release_listener.wait(timeout=5)),
    )

    try:
        started = time.monotonic()
        request = Request(channel.url, data=_event_body(1), method='POST')
        with urlopen(request, timeout=1) as response:
            assert response.status == 204

        assert time.monotonic() - started < 0.5
        assert listener_started.wait(timeout=1)
    finally:
        release_listener.set()
        channel.close()
