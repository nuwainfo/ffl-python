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

import tempfile

from collections.abc import Iterable
from typing import BinaryIO
from pathlib import Path
from typing import Any

from . import _generated
from .events import FFLHookEventChannel
from .models import DownloadResult, DownloadSession, KeygenResult, ShareSession
from .parsing import FFLResultParser


class FFLClient:
    """High-level FFL API built on the bundled subprocess layer."""

    @staticmethod
    def _normalize_optional_value(value: str | bool | None) -> str | bool | None:
        if value == '':
            return True
        return value

    def _share_temporary_bytes(
        self,
        data: bytes,
        name: str,
        share_options: dict[str, Any],
    ) -> ShareSession:
        suffix = Path(name).suffix
        temporary_file = tempfile.NamedTemporaryFile(
            prefix='ffl-python-',
            suffix=suffix,
            delete=False,
        )
        temporary_path = Path(temporary_file.name)
        try:
            temporary_file.write(data)
            temporary_file.close()
            session = self.share(temporary_path, name=name, **share_options)
        except Exception:
            temporary_file.close()
            temporary_path.unlink(missing_ok=True)
            raise
        return session.attach_cleanup_paths((temporary_path,))

    def version(self) -> str:
        return _generated.version(version=True)

    def share(
        self,
        paths: str | Path | Iterable[str | Path],
        *,
        name: str | None = None,
        e2ee: bool = False,
        auth_user: str | None = None,
        auth_password: str | None = None,
        max_downloads: int | None = None,
        timeout_seconds: int | None = None,
        hook_url: str | None = None,
        capture_hook_events: bool = True,
        event_history_limit: int = 1000,
        proxy: str | None = None,
        exclude: str | None = None,
        recipient_auth: str | None = None,
        pickup_code: str | None = None,
        recipient_public_key: str | Path | None = None,
        recipient_email: str | None = None,
        recipient_otp_api_base: str | None = None,
        alias: str | None = None,
        receipt: str | bool | None = None,
        receipt_confirm: str | bool | None = None,
        force_relay: bool = False,
        upload: str | bool | None = None,
        resume_upload: bool = False,
        vfs: bool = False,
        preferred_tunnel: str | None = None,
        port: int | None = None,
        invite: bool = False,
        pause: int | None = None,
        enable_reporting: bool = False,
        qr: str | Path | bool | None = None,
        stdin_cache: str | None = None,
        log_level: str | None = None,
        stdin: BinaryIO | None = None,
    ) -> ShareSession:
        event_channel = (
            FFLHookEventChannel(hook_url, event_history_limit)
            if capture_hook_events
            else None
        )
        try:
            session = _generated.share(
                paths=paths,
                log_level=log_level,
                proxy=proxy,
                hook=hook_url if event_channel is None else event_channel.url,
                enable_reporting=enable_reporting,
                name=name,
                exclude=exclude,
                upload=self._normalize_optional_value(upload),
                resume=resume_upload,
                pause=pause,
                max_downloads=max_downloads,
                timeout=timeout_seconds,
                port=port,
                auth_user=auth_user,
                auth_password=auth_password,
                recipient_auth=recipient_auth,
                pickup_code=pickup_code,
                recipient_public_key=recipient_public_key,
                recipient_email=recipient_email,
                recipient_otp_api_base=recipient_otp_api_base,
                force_relay=force_relay,
                e2ee=e2ee,
                invite=invite,
                qr=self._normalize_optional_value(qr),
                disable_clipboard=True,
                vfs=vfs,
                stdin_cache=stdin_cache,
                foreground=True,
                alias=alias,
                receipt=self._normalize_optional_value(receipt),
                receipt_confirm=self._normalize_optional_value(receipt_confirm),
                preferred_tunnel=preferred_tunnel,
                stdin=stdin,
            )
        except Exception:
            if event_channel is not None:
                event_channel.close()
            raise
            
        return ShareSession(session, event_channel=event_channel)

    def share_text(
        self,
        text: str,
        name: str = 'shared.txt',
        **share_options: Any,
    ) -> ShareSession:
        return self._share_temporary_bytes(
            text.encode('utf-8'),
            name,
            share_options,
        )

    def share_bytes(
        self,
        data: bytes,
        name: str = 'data.bin',
        **share_options: Any,
    ) -> ShareSession:
        return self._share_temporary_bytes(data, name, share_options)

    def share_stream(
        self,
        source: BinaryIO,
        name: str = 'stream.bin',
        **share_options: Any,
    ) -> ShareSession:
        return self.share(
            '-',
            name=name,
            stdin=source,
            stdin_cache=share_options.pop('stdin_cache', 'off'),
            **share_options,
        )

    def download(
        self,
        url: str,
        *,
        output_path: str | Path | None = None,
        resume: bool = False,
        auth_user: str | None = None,
        auth_password: str | None = None,
        proxy: str | None = None,
        recipient_auth: str | None = None,
        pickup_code: str | None = None,
        recipient_private_key: str | Path | None = None,
        enable_reporting: bool = False,
        hook_url: str | None = None,
        log_level: str | None = None,
    ) -> DownloadResult:
        return self.start_download(
            url,
            output_path=output_path,
            resume=resume,
            auth_user=auth_user,
            auth_password=auth_password,
            proxy=proxy,
            recipient_auth=recipient_auth,
            pickup_code=pickup_code,
            recipient_private_key=recipient_private_key,
            enable_reporting=enable_reporting,
            hook_url=hook_url,
            log_level=log_level,
        ).wait()

    def start_download(
        self,
        url: str,
        *,
        output_path: str | Path | None = None,
        resume: bool = False,
        auth_user: str | None = None,
        auth_password: str | None = None,
        proxy: str | None = None,
        recipient_auth: str | None = None,
        pickup_code: str | None = None,
        recipient_private_key: str | Path | None = None,
        enable_reporting: bool = False,
        hook_url: str | None = None,
        log_level: str | None = None,
    ) -> DownloadSession:
        return self._start_download(
            url,
            output_path=output_path,
            resume=resume,
            auth_user=auth_user,
            auth_password=auth_password,
            proxy=proxy,
            recipient_auth=recipient_auth,
            pickup_code=pickup_code,
            recipient_private_key=recipient_private_key,
            enable_reporting=enable_reporting,
            hook_url=hook_url,
            log_level=log_level,
            stream_stdout=False,
        )

    def _start_download(
        self,
        url: str,
        *,
        output_path: str | Path | None = None,
        resume: bool = False,
        auth_user: str | None = None,
        auth_password: str | None = None,
        proxy: str | None = None,
        recipient_auth: str | None = None,
        pickup_code: str | None = None,
        recipient_private_key: str | Path | None = None,
        enable_reporting: bool = False,
        hook_url: str | None = None,
        log_level: str | None = None,
        stream_stdout: bool,
    ) -> DownloadSession:
        cwd = Path.cwd()
        process = _generated.download(
            url=url,
            log_level=log_level,
            proxy=proxy,
            hook=hook_url,
            enable_reporting=enable_reporting,
            output_path=output_path,
            resume=resume,
            auth_user=auth_user,
            auth_password=auth_password,
            recipient_auth=recipient_auth,
            pickup_code=pickup_code,
            recipient_private_key=recipient_private_key,
            stdout=stream_stdout,
            _apebind_capture_stdout=not stream_stdout,
        )

        session = DownloadSession(
            process,
            output_path,
            lambda result, requested_path: FFLResultParser.parse_download(
                result,
                requested_path,
                cwd,
            ),
        )
        return session

    def download_stream(
        self,
        url: str,
        **download_options: Any,
    ) -> DownloadSession:
        if 'output_path' in download_options:
            raise TypeError('download_stream writes to stdout and does not accept output_path')

        return self._start_download(
            url,
            stream_stdout=True,
            **download_options,
        )

    def keygen(
        self,
        name: str | None = None,
        *,
        enable_reporting: bool = False,
        log_level: str | None = None,
    ) -> KeygenResult:
        cwd = Path.cwd()
        process = _generated.keygen(
            name=name,
            enable_reporting=enable_reporting,
            log_level=log_level,
        )
        return FFLResultParser.parse_keygen(process, cwd)

    def raw(self, arguments: list[str], persistent: bool = False):
        return _generated.raw(arguments, persistent=persistent)
