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

"""Send with ``ffl.py``, receive with a real, Selenium-driven browser.

FastFileLink has no browser-based *upload* UI -- sharing always starts from
the CLI/library -- so the sending side here still uses :mod:`ffl_demo`. The
*receiving* side is the part this script demonstrates: it drives an actual
Chrome browser to the share link, exactly like a human recipient would, and
waits for the browser's own download manager to save the file.

Requires ``pip install selenium`` and a local Chrome/Chromium install.
Selenium Manager (bundled with selenium>=4.6) downloads a matching
chromedriver automatically -- no manual driver setup needed.

Run from the repository root (after ``pip install -e ".[dev]"``)::

    python examples/selenium_receive_demo.py
    python examples/selenium_receive_demo.py --no-headless   # watch it happen
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ffl_demo import send  # noqa: E402  (needs sys.path tweak above)

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait
except ImportError as error:  # pragma: no cover - developer guidance only
    raise SystemExit(
        "This demo needs Selenium. Install it with: pip install selenium"
    ) from error


def _build_driver(download_dir: Path, *, headless: bool) -> webdriver.Chrome:
    options = Options()
    if headless:
        options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_experimental_option(
        'prefs',
        {
            'download.default_directory': str(download_dir),
            'download.prompt_for_download': False,
            'safebrowsing.enabled': True,
        },
    )

    driver = webdriver.Chrome(options=options)
    # Headless Chrome blocks downloads unless explicitly allowed via CDP.
    driver.execute_cdp_cmd(
        'Page.setDownloadBehavior',
        {'behavior': 'allow', 'downloadPath': str(download_dir)},
    )
    return driver


def _wait_for_download(download_dir: Path, timeout: float) -> Path | None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        finished = [p for p in download_dir.iterdir() if not p.name.endswith('.crdownload')]
        if finished:
            return finished[0]
        time.sleep(0.5)
    return None


def _receive_via_browser(link: str, download_dir: Path, *, headless: bool) -> Path:
    driver = _build_driver(download_dir, headless=headless)
    try:
        driver.get(link)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, 'download-link'))
        )

        # FFL's page negotiates WebRTC P2P (falling back to HTTP itself if
        # that fails) and starts the download on its own -- no click needed.
        downloaded = _wait_for_download(download_dir, timeout=45)
        if downloaded is None:
            raise RuntimeError('Browser did not save a downloaded file in time')

        return downloaded
    finally:
        driver.quit()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--no-headless',
        action='store_false',
        dest='headless',
        help='Show the Chrome window instead of running headless.',
    )
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix='ffl-python-demo-') as work_dir:
        work_dir = Path(work_dir)
        source = work_dir / 'source.txt'
        download_dir = work_dir / 'browser-downloads'
        download_dir.mkdir()
        payload = 'Hello from ffl.py, received by a real Selenium-driven browser.\n'
        source.write_text(payload, encoding='utf-8')

        print(f'Sharing {source} ...')
        with send(source, name='selenium-demo.txt', max_downloads=1, timeout_seconds=180) as session:
            print(f'Link: {session.link}')

            print(f'Opening the link in Chrome (headless={args.headless}) ...')
            downloaded = _receive_via_browser(session.link, download_dir, headless=args.headless)
            print(f'Browser saved: {downloaded}')

            session.wait()

        received_text = downloaded.read_text(encoding='utf-8')
        if received_text != payload:
            print('Mismatch between sent and received content!', file=sys.stderr)
            return 1

        print('Success: the browser downloaded exactly what was shared.')
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
