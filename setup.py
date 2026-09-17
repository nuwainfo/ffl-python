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

from pathlib import Path
from tempfile import NamedTemporaryFile
from zipfile import ZIP_DEFLATED, ZipFile

from setuptools import setup
from wheel.bdist_wheel import bdist_wheel


class _FFLWheel(bdist_wheel):
    def run(self) -> None:
        super().run()

        for wheel_path in Path(self.dist_dir).glob('*.whl'):
            self._mark_ape_executable(wheel_path)

    @staticmethod
    def _mark_ape_executable(wheel_path: Path) -> None:
        with ZipFile(wheel_path) as source:
            entries = [
                (info, source.read(info.filename))
                for info in source.infolist()
            ]

        with NamedTemporaryFile(delete=False, dir=wheel_path.parent) as temporary:
            temporary_path = Path(temporary.name)

        try:
            with ZipFile(temporary_path, 'w', ZIP_DEFLATED) as target:
                for info, contents in entries:
                    if info.filename == 'ffl/bin/ffl.com':
                        info.create_system = 3
                        info.external_attr = 0o100755 << 16
                    target.writestr(info, contents)
                    
            temporary_path.replace(wheel_path)
        finally:
            temporary_path.unlink(missing_ok=True)


setup(cmdclass={'bdist_wheel': _FFLWheel})
