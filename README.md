# ffl-python

Python binding for FastFileLink. The package bundles the portable `ffl.com` APE and
runs it behind a Python API; callers do not need to locate or install a separate FFL
binary.

## Installation

```bash
pip install ffl-python
```

This installs the `ffl` package with the bundled `ffl.com` APE included -- no separate
FFL install or PATH setup required.

## Development

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"   # Windows
# or: .venv/bin/python -m pip install -e ".[dev]"

.\scripts\test.ps1                 # Windows
# or: ./scripts/test.sh              # Linux/macOS

.\scripts\build.ps1                # Windows
# or: ./scripts/build.sh             # Linux/macOS
```

## Share

```python
import ffl

with ffl.share("release.zip", max_downloads=1, timeout_seconds=1800) as session:
    print(session.link)
```

`share()` always requests a foreground FFL process and disables clipboard side effects,
which gives library callers a deterministic `ShareSession` they can stop or keep alive.
FFL's runtime-owned `--json` output is used internally to wait until `session.link` is
ready.

Multiple files are accepted directly:

```python
session = ffl.share(["one.txt", "two.txt"], name="files.zip")
```

Text and bytes helpers own their temporary file until the share session is closed:

```python
with ffl.share_text("hello", name="hello.txt") as session:
    print(session.link)
```

### Stream a source without a temporary file

`share_stream()` passes a binary file-like object directly to FFL stdin. It is useful
for database dumps, generated artifacts, and other data that should not first be
materialized as a separate temporary file:

```python
with open("backup.tar", "rb") as source:
    with ffl.share_stream(source, name="backup.tar") as session:
        print(session.link)
```

## Download

```python
result = ffl.download("https://example.fastfilelink/...", output_path="download.bin")
print(result.output_path)
print(result.transfer_mode)
```

`download()` waits for the foreground FFL process to finish and returns a
`DownloadResult`. For cancellation, progress, or caller-controlled timeouts, use
`start_download()` and manage its `DownloadSession` explicitly.

### Stream a download

`download_stream()` exposes FFL stdout as binary chunks without buffering the whole
file in memory:

```python
with ffl.download_stream("https://example.fastfilelink/...") as transfer:
    with open("output.bin", "wb") as target:
        for chunk in transfer.iter_bytes():
            target.write(chunk)

    result = transfer.wait()
```

Consume `iter_bytes()` through EOF before calling `wait()`. Calling `wait()` with
unconsumed streamed stdout raises `RuntimeError`; this avoids silently discarding
binary data or deadlocking when the child process fills its stdout pipe.

## Authentication secrets

For shares protected with HTTP Basic Auth, FFL supports `FFL_AUTH_PASSWORD`. Set it in
the application environment and pass only `auth_user` to keep the password out of the
FFL command line:

```bash
export FFL_AUTH_PASSWORD='use-your-secret-manager'
```

```powershell
$env:FFL_AUTH_PASSWORD = 'use-your-secret-manager'
```

```python
with ffl.share("release.zip", auth_user="deploy") as session:
    print(session.link)
```

Do not also pass `auth_password=` when using this pattern: FFL gives the explicit CLI
option precedence over `FFL_AUTH_PASSWORD`. The environment variable applies to the
sharing side; pass download credentials explicitly when downloading a protected link.

## Key generation

```python
result = ffl.keygen("alice")
print(result.public_key_path)
print(result.private_key_path)
```

## Version and raw access

```python
print(ffl.version())
result = ffl.raw(["download", "--help"])
```

`raw()` is the escape hatch for new FFL options or commands that the semantic API has
not adopted yet.
