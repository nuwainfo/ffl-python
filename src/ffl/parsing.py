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

import re
from pathlib import Path

from ._runtime import APEProcessResult
from .errors import FFLOutputError
from .models import DownloadResult, KeygenResult, TransferMode


class FFLResultParser:
    _DOWNLOADED_RE = re.compile(r'^Downloaded:\s+(.+)$', re.MULTILINE)
    _DOWNLOADING_RE = re.compile(r'Downloading\s+(.+?)\s+\(')
    _PRIVATE_KEY_RE = re.compile(r'^\s*Private key\s*:\s*(.+?)\s*$', re.MULTILINE)
    _PUBLIC_KEY_RE = re.compile(
        r'^\s*Public key\s*:\s*(.+?)(?:\s+←.*)?$',
        re.MULTILINE,
    )

    @staticmethod
    def _combined_output(process: APEProcessResult) -> str:
        return '\n'.join(part for part in (process.stdout, process.stderr) if part)

    @classmethod
    def _detect_transfer_mode(cls, output: str) -> TransferMode:
        if 'P2P direct' in output or 'WebRTC P2P' in output:
            return TransferMode.WEBRTC_P2P
        if 'P2P UDP/QUIC' in output:
            return TransferMode.P2P_QUIC
        if 'P2P TCP' in output:
            return TransferMode.P2P_TCP
        if 'HTTP fallback' in output:
            return TransferMode.HTTP_FALLBACK
        if (
            'HTTP download' in output
            or 'downloading directly via HTTP' in output
            or 'WebRTC not supported' in output
        ):
            return TransferMode.HTTP_DIRECT
            
        return TransferMode.UNKNOWN

    @classmethod
    def _detect_download_path(cls, output: str, cwd: Path) -> Path | None:
        match = cls._DOWNLOADED_RE.search(output)
        if match is None:
            match = cls._DOWNLOADING_RE.search(output)
            
        if match is None:
            return None
            
        return (cwd / match.group(1).strip()).resolve()

    @classmethod
    def parse_download(
        cls,
        process: APEProcessResult,
        requested_output_path: str | Path | None,
        cwd: Path,
    ) -> DownloadResult:
        output = cls._combined_output(process)
        if requested_output_path is not None:
            output_path = Path(requested_output_path).expanduser().resolve()
        else:
            output_path = cls._detect_download_path(output, cwd)
            
        return DownloadResult(
            process=process,
            output_path=output_path,
            transfer_mode=cls._detect_transfer_mode(output),
        )

    @classmethod
    def parse_keygen(cls, process: APEProcessResult, cwd: Path) -> KeygenResult:
        output = cls._combined_output(process)
        private_match = cls._PRIVATE_KEY_RE.search(output)
        public_match = cls._PUBLIC_KEY_RE.search(output)
        if private_match is None or public_match is None:
            raise FFLOutputError('FFL keygen output did not contain both key paths')

        private_key_path = (cwd / private_match.group(1).strip()).resolve()
        public_key_path = (cwd / public_match.group(1).strip()).resolve()
        
        if not private_key_path.is_file() or not public_key_path.is_file():
            raise FFLOutputError('FFL keygen reported key files that do not exist')
            
        return KeygenResult(
            process=process,
            private_key_path=private_key_path,
            public_key_path=public_key_path,
        )
