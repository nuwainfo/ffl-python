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

from enum import IntEnum
from pathlib import Path
from collections.abc import Callable
from typing import Iterator

from ._runtime import APEProcessResult, ProcessSession
from .errors import FFLDownloadAbortedError
from .events import FFLHookEvent, FFLHookEventChannel


class TransferMode(IntEnum):
    UNKNOWN = 1
    WEBRTC_P2P = 2
    HTTP_FALLBACK = 3
    HTTP_DIRECT = 4
    P2P_TCP = 5
    P2P_QUIC = 6


class ShareSession:
    """Own a foreground FFL share process and any temporary source files."""

    def __init__(
        self,
        session: ProcessSession,
        cleanup_paths: tuple[Path, ...] = (),
        event_channel: FFLHookEventChannel | None = None,
    ):
        self._session = session
        self._cleanup_paths = cleanup_paths
        self._event_channel = event_channel
        self._session.on_exit(self._cleanup)

    @property
    def argv(self) -> tuple[str, ...]:
        return self._session.argv

    @property
    def link(self) -> str:
        link = self._session.result
        if not isinstance(link, str) or not link:
            raise RuntimeError('FFL share session does not have a valid link result')
            
        return link

    @property
    def pid(self) -> int:
        return self._session.pid

    @property
    def running(self) -> bool:
        return self._session.running

    @property
    def return_code(self) -> int | None:
        return self._session.return_code

    @property
    def stdout(self):
        return self._session.stdout

    @property
    def stderr(self):
        return self._session.stderr

    def _cleanup(self) -> None:
        for path in self._cleanup_paths:
            path.unlink(missing_ok=True)
            
        self._cleanup_paths = ()
        
        if self._event_channel is not None:
            self._event_channel.close()

    @property
    def event_history(self) -> tuple[FFLHookEvent, ...]:
        if self._event_channel is None:
            return ()
            
        return self._event_channel.history

    def on(self, name: str, listener: Callable[[FFLHookEvent], None]) -> None:
        if self._event_channel is None:
            raise RuntimeError('FFL share session does not have an event channel')
            
        self._event_channel.on_semantic(name, listener)

    def on_raw(self, name: str, listener: Callable[[FFLHookEvent], None]) -> None:
        if self._event_channel is None:
            raise RuntimeError('FFL share session does not have an event channel')
            
        self._event_channel.on(name, listener)

    def events(self) -> Iterator[FFLHookEvent]:
        if self._event_channel is None:
            return iter(())
            
        return self._event_channel.events()

    def raw_events(self) -> Iterator[FFLHookEvent]:
        return self.events()

    def _raise_event_error(self) -> None:
        if self._event_channel is not None:
            self._event_channel.raise_if_error()

    def attach_cleanup_paths(self, paths: tuple[Path, ...]) -> ShareSession:
        self._cleanup_paths = (*self._cleanup_paths, *paths)
        return self

    def iter_stdout(self) -> Iterator[str]:
        yield from self._session.iter_stdout()

    def wait(self, timeout: float | None = None) -> int:
        try:
            result = self._session.wait(timeout=timeout)
            self._raise_event_error()
            return result
        finally:
            if not self._session.running:
                self._cleanup()

    def stop(self, timeout: float = 5.0) -> None:
        try:
            self._session.stop(timeout=timeout)
            self._raise_event_error()
        finally:
            self._cleanup()

    def close(self) -> None:
        try:
            self._session.close()
            self._raise_event_error()
        finally:
            self._cleanup()

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback_value) -> None:
        del exception_type, exception_value, traceback_value
        self.close()


class DownloadResult:
    def __init__(
        self,
        process: APEProcessResult,
        output_path: Path | None,
        transfer_mode: TransferMode,
    ):
        self.process = process
        self.output_path = output_path
        self.transfer_mode = transfer_mode

    @property
    def argv(self) -> tuple[str, ...]:
        return self.process.argv

    @property
    def return_code(self) -> int:
        return self.process.return_code

    @property
    def stdout(self) -> str:
        return self.process.stdout

    @property
    def stderr(self) -> str:
        return self.process.stderr


class DownloadSession:
    """Own a foreground FFL download process until it completes or is stopped."""

    def __init__(
        self,
        session: ProcessSession,
        output_path: str | Path | None,
        parse_result: Callable[[APEProcessResult, str | Path | None], DownloadResult],
    ):
        self._session = session
        self._output_path = output_path
        self._parse_result = parse_result
        self._abort_error: FFLDownloadAbortedError | None = None

    @property
    def argv(self) -> tuple[str, ...]:
        return self._session.argv

    @property
    def pid(self) -> int:
        return self._session.pid

    @property
    def running(self) -> bool:
        return self._session.running

    @property
    def return_code(self) -> int | None:
        return self._session.return_code

    @property
    def cancelled(self) -> bool:
        return self._abort_error is not None

    def wait(self, timeout: float | None = None) -> DownloadResult:
        self._session.wait(timeout)
        if self._abort_error is not None:
            raise self._abort_error
            
        return self._parse_result(self._session.process_result, self._output_path)

    def iter_bytes(self) -> Iterator[bytes]:
        yield from self._session.iter_stdout_bytes()

    def abort(self, timeout: float = 5.0) -> None:
        if self._abort_error is None:
            self._abort_error = FFLDownloadAbortedError('FFL download was aborted')
            
        self._session.stop(timeout)

    def stop(self, timeout: float = 5.0) -> None:
        self.abort(timeout)

    def close(self) -> None:
        if self.running:
            self.abort()
            return

        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback_value) -> None:
        del exception_type, exception_value, traceback_value
        self.close()


class KeygenResult:
    def __init__(
        self,
        process: APEProcessResult,
        private_key_path: Path,
        public_key_path: Path,
    ):
        self.process = process
        self.private_key_path = private_key_path
        self.public_key_path = public_key_path

    @property
    def argv(self) -> tuple[str, ...]:
        return self.process.argv

    @property
    def return_code(self) -> int:
        return self.process.return_code

    @property
    def stdout(self) -> str:
        return self.process.stdout

    @property
    def stderr(self) -> str:
        return self.process.stderr
