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

"""Send and receive a file using only the ``ffl`` Python API.

Both sides of the transfer run in this one script: it shares a temporary
file, downloads it back with :func:`ffl.download`, and checks the bytes
round-tripped correctly. No browser is involved.

Run from the repository root (after ``pip install -e ".[dev]"``)::

    python examples/python_send_receive.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ffl_demo import receive, send  # noqa: E402  (needs sys.path tweak above)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix='ffl-python-demo-') as work_dir:
        work_dir = Path(work_dir)
        source = work_dir / 'source.txt'
        destination = work_dir / 'received.txt'
        payload = 'Hello from ffl.py, sent and received without a browser.\n'
        source.write_text(payload, encoding='utf-8')

        print(f'Sharing {source} ...')
        with send(source, name='python-demo.txt', max_downloads=1, timeout_seconds=120) as session:
            print(f'Link: {session.link}')

            print(f'Downloading to {destination} ...')
            result = receive(session.link, output_path=destination)

        print(f'Transfer mode: {result.transfer_mode.name}')
        print(f'Return code:   {result.return_code}')

        received_text = destination.read_text(encoding='utf-8')
        if received_text != payload:
            print('Mismatch between sent and received content!', file=sys.stderr)
            return 1

        print('Success: sent and received content match.')
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
