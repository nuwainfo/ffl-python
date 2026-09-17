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

"""Minimal send/receive helpers built on the ``ffl`` package.

This is the smallest useful wrapper around the library: ``send()`` shares a
file and hands back the still-running session, ``receive()`` downloads a
link. Both ``python_send_receive.py`` and ``selenium_receive_demo.py`` in
this folder import these two functions instead of calling ``ffl`` directly.

Note: this file is intentionally *not* named ``ffl.py``. Running a script
with the same name as an imported package shadows the real package (Python
puts the script's own directory first on ``sys.path``), so ``import ffl``
inside it would resolve to itself instead of the installed library.

Usable directly from the command line too::

    python ffl_demo.py send some_file.txt
    python ffl_demo.py receive https://.../abcd1234 -o downloaded.txt
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import ffl


def send(
    path: str | Path,
    *,
    name: str | None = None,
    max_downloads: int = 1,
    timeout_seconds: int = 300,
) -> ffl.ShareSession:
    """Start sharing ``path`` and return the still-running session.

    The share keeps running in the foreground until it has been downloaded
    ``max_downloads`` times or ``timeout_seconds`` elapses. The caller owns
    the returned session: use it as a context manager, or call
    ``session.wait()`` / ``session.stop()`` explicitly once the link no
    longer needs to stay live.
    """
    return ffl.share(
        path,
        name=name,
        max_downloads=max_downloads,
        timeout_seconds=timeout_seconds,
    )


def receive(url: str, *, output_path: str | Path | None = None) -> ffl.DownloadResult:
    """Download ``url`` with the bundled ``ffl.com`` and return the result."""
    return ffl.download(url, output_path=output_path)


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest='command', required=True)

    send_parser = subparsers.add_parser(
        'send',
        help='Share one file and keep serving it until downloaded once or it times out.',
    )
    send_parser.add_argument('path')
    send_parser.add_argument('--name')
    send_parser.add_argument('--max-downloads', type=int, default=1)
    send_parser.add_argument('--timeout-seconds', type=int, default=300)

    receive_parser = subparsers.add_parser('receive', help='Download a shared link.')
    receive_parser.add_argument('url')
    receive_parser.add_argument('-o', '--output')

    args = parser.parse_args(argv)

    if args.command == 'send':
        with send(
            args.path,
            name=args.name,
            max_downloads=args.max_downloads,
            timeout_seconds=args.timeout_seconds,
        ) as session:
            print(session.link)
            sys.stdout.flush()
            session.wait()
        return 0

    result = receive(args.url, output_path=args.output)
    print(result.output_path)
    return result.return_code


if __name__ == '__main__':
    raise SystemExit(_main())
