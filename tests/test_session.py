from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import ffl
import pytest
from ffl import client as client_module
from ffl import _runtime as runtime_module
from ffl.models import ShareSession
from ffl._runtime import ProcessSession
from ffl.parsing import FFLResultParser


class _FakeProcessSession:
    def __init__(self):
        self._exit_listener = None

    def on_exit(self, listener):
        self._exit_listener = listener
        return self

    def exit(self):
        assert self._exit_listener is not None
        self._exit_listener()


class _FakeEventChannel:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class _FakeDownloadProcess:
    argv = ('download', 'https://example.test/file')
    pid = 1
    running = True
    return_code = None

    def wait(self, timeout=None):
        del timeout
        self.running = False
        self.return_code = 0

    @property
    def process_result(self):
        return ffl.APEProcessResult(self.argv, 0, 'Downloaded: file.bin', '')

    def stop(self, timeout=5):
        del timeout
        self.running = False
        self.return_code = 0

    def close(self):
        self.stop()

    def iter_stdout_bytes(self):
        yield b'\x00\xffpayload'


def test_share_session_stop_terminates_the_foreground_process(
    tmp_path: Path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    source = tmp_path / 'session-source.txt'
    source.write_text('Session lifecycle payload', encoding='utf-8')

    session = ffl.share(source, max_downloads=0, timeout_seconds=90)
    try:
        assert session.running
        session.stop()
        assert not session.running
        assert session.return_code is not None
    finally:
        session.close()


def test_share_session_closes_hook_channel_when_process_exits():
    process = _FakeProcessSession()
    event_channel = _FakeEventChannel()
    ShareSession(process, event_channel=event_channel)

    process.exit()

    assert event_channel.closed


def test_start_download_returns_a_cancellable_session(monkeypatch, tmp_path: Path):
    process = _FakeDownloadProcess()
    captured = {}
    monkeypatch.chdir(tmp_path)

    def download(**values):
        captured.update(values)
        return process

    monkeypatch.setattr(client_module._generated, 'download', download)
    session = client_module.FFLClient().start_download(
        'https://example.test/file',
        output_path='file.bin',
    )

    assert session.running
    assert captured['url'] == 'https://example.test/file'
    assert session.wait().output_path == (tmp_path / 'file.bin').resolve()
    assert session.return_code == 0


def test_stopping_a_download_marks_it_cancelled_and_wait_raises(monkeypatch):
    process = _FakeDownloadProcess()

    monkeypatch.setattr(client_module._generated, 'download', lambda **values: process)
    session = client_module.FFLClient().start_download('https://example.test/file')

    session.stop()

    assert session.cancelled
    with pytest.raises(ffl.FFLDownloadAbortedError):
        session.wait()


def test_closing_a_running_download_marks_it_cancelled_and_wait_raises(monkeypatch):
    process = _FakeDownloadProcess()

    monkeypatch.setattr(client_module._generated, 'download', lambda **values: process)
    session = client_module.FFLClient().start_download('https://example.test/file')

    session.close()

    assert session.cancelled
    with pytest.raises(ffl.FFLDownloadAbortedError):
        session.wait()


def test_download_stream_preserves_binary_stdout(monkeypatch):
    process = _FakeDownloadProcess()
    captured = {}

    def download(**values):
        captured.update(values)
        return process

    monkeypatch.setattr(client_module._generated, 'download', download)
    session = client_module.FFLClient().download_stream('https://example.test/file')

    assert captured['stdout'] is True
    assert captured['_apebind_capture_stdout'] is False
    assert b''.join(session.iter_bytes()) == b'\x00\xffpayload'


def test_process_session_reads_binary_stdout_without_utf8_decoding():
    process = subprocess.Popen(
        [sys.executable, '-c', "import sys; sys.stdout.buffer.write(b'\\x00\\xff')"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    session = ProcessSession(process, ['binary-child'])

    assert b''.join(session.iter_stdout_bytes()) == b'\x00\xff'
    assert session.wait() == 0
    assert process.stdout.closed
    assert process.stderr.closed


def test_streamed_stdout_is_not_retained_in_process_result():
    process = subprocess.Popen(
        [
            sys.executable,
            '-c', "import sys; sys.stdout.buffer.write(bytes([255]) * (1024 * 1024))",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    session = ProcessSession(process, ['binary-child'], capture_stdout=False)

    chunks = list(session.iter_stdout_bytes())
    assert sum(map(len, chunks)) == 1024 * 1024
    assert max(map(len, chunks)) <= 65536
    assert session.wait() == 0
    assert session.process_result.stdout == ''
    assert process.stdout.closed
    assert process.stderr.closed


def test_streamed_stdout_must_be_consumed_before_waiting():
    process = subprocess.Popen(
        [
            sys.executable,
            '-c',
            "import sys; sys.stdout.buffer.write(b'x' * (2 * 1024 * 1024))",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    session = ProcessSession(process, ['stream-child'], capture_stdout=False)

    try:
        with pytest.raises(
            RuntimeError,
            match='streamed stdout must be consumed before waiting',
        ):
            session.wait(timeout=1)
    finally:
        session.stop()


def test_launch_command_does_not_modify_the_installed_ape(monkeypatch, tmp_path: Path):
    binary_path = tmp_path / 'ffl.com'
    client = runtime_module.APEClient(binary_path, {})
    executable = str(binary_path.resolve())

    def fail_chmod(*_args, **_kwargs):
        raise AssertionError('launch must not chmod an installed APE')

    monkeypatch.setattr(runtime_module.os, 'name', 'posix')
    monkeypatch.setattr(runtime_module.Path, 'chmod', fail_chmod)

    assert client._launch_command(['version']) == [
        '/bin/sh',
        '-c',
        'exec "$0" "$@"',
        executable,
        'version',
    ]


def test_process_session_drains_large_stdout_and_stderr_before_waiting():
    process = subprocess.Popen(
        [
            sys.executable,
            '-c',
            "import sys; sys.stdout.buffer.write(b'x' * (2 * 1024 * 1024)); "
            "sys.stderr.buffer.write(b'y' * (2 * 1024 * 1024))",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    session = ProcessSession(process, ['large-output-child'])

    assert session.wait(timeout=3) == 0
    assert len(session.process_result.stdout) == 2 * 1024 * 1024
    assert len(session.process_result.stderr) == 2 * 1024 * 1024
    assert process.stdout.closed
    assert process.stderr.closed


def test_process_session_closes_stream_source_when_child_exits_early():
    class Source:
        closed = False

        def read(self, size):
            del size
            return b'x' * 65536

        def close(self):
            self.closed = True

    source = Source()
    process = subprocess.Popen(
        [
            sys.executable,
            '-c', 'import sys, time; sys.stdin.close(); time.sleep(0.01)',
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    session = ProcessSession(process, ['input-child'])
    session.attach_stdin(source)

    assert session.wait() == 0
    assert source.closed


def test_download_parser_recognizes_p2p_tcp_output(tmp_path: Path):
    process = ffl.APEProcessResult(
        ('download', 'https://example.test/file'),
        0,
        'Using P2P TCP download\nDownloaded: file.bin',
        '',
    )

    result = FFLResultParser.parse_download(process, None, tmp_path)

    assert result.transfer_mode is ffl.TransferMode.P2P_TCP


def test_download_parser_recognizes_p2p_quic_output(tmp_path: Path):
    process = ffl.APEProcessResult(
        ('download', 'https://example.test/file'),
        0,
        'Using P2P UDP/QUIC download\nDownloaded: file.bin',
        '',
    )

    result = FFLResultParser.parse_download(process, None, tmp_path)

    assert result.transfer_mode is ffl.TransferMode.P2P_QUIC


def test_download_parser_recognizes_webrtc_p2p_output(tmp_path: Path):
    process = ffl.APEProcessResult(
        ('download', 'https://example.test/file'),
        0,
        'Using WebRTC P2P download\nDownloaded: file.bin',
        '',
    )

    result = FFLResultParser.parse_download(process, None, tmp_path)

    assert result.transfer_mode is ffl.TransferMode.WEBRTC_P2P
