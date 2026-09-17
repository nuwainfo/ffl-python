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

from ._runtime import APEProcessError, APEProcessResult, ProcessSession
from .client import FFLClient
from .errors import FFLDownloadAbortedError, FFLOutputError
from .events import FFLHookEvent
from .models import DownloadResult, DownloadSession, KeygenResult, ShareSession, TransferMode


_default_client = FFLClient()

version = _default_client.version
share = _default_client.share
share_text = _default_client.share_text
share_bytes = _default_client.share_bytes
share_stream = _default_client.share_stream
download = _default_client.download
download_stream = _default_client.download_stream
start_download = _default_client.start_download
keygen = _default_client.keygen
raw = _default_client.raw

__all__ = [
    'APEProcessError',
    'APEProcessResult',
    'DownloadResult',
    'DownloadSession',
    'FFLClient',
    'FFLDownloadAbortedError',
    'FFLHookEvent',
    'FFLOutputError',
    'KeygenResult',
    'ProcessSession',
    'ShareSession',
    'TransferMode',
    'download',
    'download_stream',
    'keygen',
    'raw',
    'share',
    'share_bytes',
    'share_stream',
    'share_text',
    'start_download',
    'version',
]
