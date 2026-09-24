# ffl-python

`ffl-python` is the Python binding for the [FastFileLink](https://github.com/nuwainfo/ffl)
CLI (FFL), which turns a file, folder, or stream into a browser-ready HTTPS link so the
recipient can download it without installing anything. It prefers a direct QUIC/WebRTC P2P
connection and falls back to a relayed/tunneled HTTPS link, with optional end-to-end
encryption. See the FFL repository for the full protocol and CLI details.

The package bundles the portable `ffl.com` APE and runs it behind a Python API, 
powered by [APEBind](https://github.com/nuwainfo/apebind), 
so callers do not need to locate or install a separate FFL 

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

## Compared to magic-wormhole

[magic-wormhole](https://github.com/magic-wormhole/magic-wormhole) is the other Python
tool commonly reached for to move a file between two machines. Both are ad hoc,
non-account-based transfers you can drive from Python, but they differ in shape:

- **Binding vs. native library.** `ffl-python` is a subprocess wrapper around the
  separate `ffl.com` CLI binary -- WebRTC/QUIC, NAT traversal, and relay/tunnel fallback
  all happen in that external process. `wormhole` is a native, in-process Python package
  (Twisted-based); no external binary is involved. In practice, though, wormhole's own
  *file*-transfer path is also driven through its CLI machinery rather than a stable
  public library call -- `wormhole.create()` covers generic message exchange, not file
  transfer directly.
- **Recipient experience.** An FFL share is an HTTPS link: the recipient opens it in a
  browser and downloads, no install required. A wormhole transfer is a short code
  (e.g. `7-crossbow-clockwork`) exchanged out-of-band; the recipient needs the
  `wormhole` CLI installed to redeem it.
- **Transport.** FFL tries a direct WebRTC/QUIC P2P connection first, falls back to a
  plain P2P TCP connection, and falls back again to a relayed/tunneled HTTPS link if no
  P2P path is reachable at all. wormhole's own transit protocol does direct TCP with a
  relay fallback, with the connection authenticated by a SPAKE2 PAKE key derived from the
  code.
- **Security default.** wormhole is end-to-end encrypted on every transfer by
  construction of the code exchange. FFL's end-to-end encryption is opt-in (`--e2ee`);
  without it, data in transit is only as protected as the HTTPS connection to FFL's
  relay/tunnel infrastructure.
- **Feature surface.** FFL adds application-layer conveniences wormhole doesn't have: a
  secondary pickup-code/public-key recipient check layered on top of the link,
  receipt-confirmation emails, a pluggable choice of tunnel backend when P2P isn't
  reachable (built-in `default`, plus Cloudflare, ngrok, Localtunnel, Loophole, Dev
  Tunnel, Bore, or a self-hosted sish tunnel via `--preferred-tunnel`, with custom
  tunnels configurable in `~/.fastfilelink/tunnels.json`), and general SOCKS5/HTTP
  proxy configuration (wormhole only knows how to route through Tor, via `--tor`).
  
