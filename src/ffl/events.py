#!/usr/bin/env python
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
#
# FastFileLink CLI - Fast, no-fuss file sharing
# Copyright (C) 2025-2026 FastFileLink contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import json
import queue
import threading

from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


_SEMANTIC_EVENT_NAMES = {
    '/hook/server/endpoints/register': 'ready',
    '/hook/transfer/progress': 'progress',
    '/hook/transfer/transport': 'transport',
    '/hook/transfer/complete': 'completed',
}


@dataclass(frozen=True)
class FFLHookEvent:
    """An event emitted by FFL's HTTP hook transport."""

    name: str
    timestamp: str | None
    data: Mapping[str, Any]
    raw: Mapping[str, Any]

    @property
    def semantic_name(self) -> str | None:
        return _SEMANTIC_EVENT_NAMES.get(self.name)


class FFLHookEventChannel:
    """Own a local FFL hook endpoint and project its JSON payloads as events."""

    def __init__(
        self,
        forward_url: str | None = None,
        event_history_limit: int = 1000,
    ):
        if isinstance(event_history_limit, bool) or not isinstance(event_history_limit, int):
            raise TypeError('event_history_limit must be an integer')

        if event_history_limit < 1:
            raise ValueError('event_history_limit must be a positive integer')

        self._forward_url = forward_url
        self._event_history_limit = event_history_limit
        self._history: list[FFLHookEvent] = []
        self._listeners: dict[str, list[Callable[[FFLHookEvent], None]]] = {}
        self._semantic_listeners: dict[
            str,
            list[Callable[[FFLHookEvent], None]],
        ] = {}
        self._iterators: set[queue.Queue[FFLHookEvent | None]] = set()
        self._listener_queue: queue.Queue[
            tuple[Callable[[FFLHookEvent], None], FFLHookEvent] | None
        ] = queue.Queue()
        self._lock = threading.Lock()
        self._error: Exception | None = None
        self._closed = False
        
        self._server = ThreadingHTTPServer(('127.0.0.1', 0), self._handler())
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name='ffl-python-hook',
            daemon=True,
        )
        self._listener_thread = threading.Thread(
            target=self._dispatch_listeners,
            name='ffl-python-hook-listeners',
            daemon=True,
        )
        self._listener_thread.start()
        self._thread.start()

    @property
    def url(self) -> str:
        return f'http://127.0.0.1:{self._server.server_port}/events'

    @property
    def history(self) -> tuple[FFLHookEvent, ...]:
        with self._lock:
            return tuple(self._history)

    def on(self, name: str, listener: Callable[[FFLHookEvent], None]) -> None:
        with self._lock:
            self._listeners.setdefault(name, []).append(listener)
            replay = tuple(event for event in self._history if event.name == name)

        for event in replay:
            self._call_listener(listener, event)

    def on_semantic(self, name: str, listener: Callable[[FFLHookEvent], None]) -> None:
        with self._lock:
            self._semantic_listeners.setdefault(name, []).append(listener)
            replay = tuple(
                event for event in self._history if event.semantic_name == name
            )

        for event in replay:
            self._call_listener(listener, event)

    def events(self) -> Iterator[FFLHookEvent]:
        event_queue: queue.Queue[FFLHookEvent | None] = queue.Queue()
        with self._lock:
            for event in self._history:
                event_queue.put(event)
                
            if not self._closed:
                self._iterators.add(event_queue)
            else:
                event_queue.put(None)

        try:
            while True:
                event = event_queue.get()
                if event is None:
                    return
                    
                yield event
        finally:
            with self._lock:
                self._iterators.discard(event_queue)

    def raise_if_error(self) -> None:
        if self._error is not None:
            raise RuntimeError('FFL hook event handling failed') from self._error

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
                
            self._closed = True
            iterator_queues = tuple(self._iterators)

        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)
        self._listener_queue.put(None)
        for event_queue in iterator_queues:
            event_queue.put(None)

    def _handler(self):
        channel = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                content_length = int(self.headers.get('Content-Length', '0'))
                body = self.rfile.read(content_length)
                published = False
                try:
                    channel._publish(body)
                    published = True
                    self.send_response(204)
                except Exception as error:
                    channel._record_error(error)
                    self.send_response(500)
                    
                self.end_headers()

                if published and channel._forward_url is not None:
                    channel._forward_async(body)

            def log_message(self, format_string: str, *args) -> None:
                del format_string, args

        return Handler

    def _publish(self, body: bytes) -> None:
        raw = json.loads(body.decode('utf-8'))
        if not isinstance(raw, dict):
            raise TypeError('FFL hook payload must be a JSON object')

        name = raw.get('event')
        if not isinstance(name, str) or not name:
            raise ValueError('FFL hook payload is missing its event name')

        timestamp = raw.get('timestamp')
        if timestamp is not None and not isinstance(timestamp, str):
            raise TypeError('FFL hook event timestamp must be a string')

        data = raw.get('data', {})
        if not isinstance(data, dict):
            raise TypeError('FFL hook event data must be a JSON object')

        event = FFLHookEvent(name, timestamp, data, raw)
        with self._lock:
            self._history.append(event)
            if len(self._history) > self._event_history_limit:
                self._history.pop(0)
                
            iterator_queues = tuple(self._iterators)
            listeners = tuple(self._listeners.get(name, ()))
            semantic_listeners = tuple(
                self._semantic_listeners.get(event.semantic_name, ())
            )
            self._enqueue_listeners(listeners, (event,))
            self._enqueue_listeners(semantic_listeners, (event,))

        for event_queue in iterator_queues:
            event_queue.put(event)

    def _enqueue_listeners(
        self,
        listeners: tuple[Callable[[FFLHookEvent], None], ...],
        events: tuple[FFLHookEvent, ...],
    ) -> None:
        for event in events:
            for listener in listeners:
                self._listener_queue.put((listener, event))

    def _dispatch_listeners(self) -> None:
        while True:
            item = self._listener_queue.get()
            if item is None:
                return

            listener, event = item
            self._call_listener(listener, event)

    def _forward_async(self, body: bytes) -> None:
        threading.Thread(
            target=self._forward,
            args=(body,),
            name='ffl-python-hook-forward',
            daemon=True,
        ).start()

    def _forward(self, body: bytes) -> None:
        request = Request(
            self._forward_url,
            data=body,
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        try:
            with urlopen(request, timeout=3):
                pass
        except (TimeoutError, URLError):
            pass

    def _call_listener(
        self,
        listener: Callable[[FFLHookEvent], None],
        event: FFLHookEvent,
    ) -> None:
        try:
            listener(event)
        except Exception as error:
            self._record_error(error)

    def _record_error(self, error: Exception) -> None:
        with self._lock:
            if self._error is None:
                self._error = error
