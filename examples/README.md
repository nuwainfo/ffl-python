# ffl-python examples

Runnable demos of the `ffl` package. All of them need working network access
to FastFileLink (same requirement as the test suite).

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"   # from the repo root
```

## `ffl_demo.py`

The smallest useful wrapper: `send(path)` shares a file and returns the
still-running session, `receive(url)` downloads a link. The other two demos
import these two functions. It also works as a small CLI on its own:

```bash
python examples/ffl_demo.py send some_file.txt
# prints the link, then blocks, serving the file until it's downloaded
# once (or --timeout-seconds elapses)

python examples/ffl_demo.py receive https://.../abcd1234 -o downloaded.txt
```

It is deliberately not called `ffl.py`: a script with the same name as an
imported package shadows that package (Python puts the script's own
directory first on `sys.path`), so `import ffl` inside it would import
itself instead of the installed library.

## `python_send_receive.py`

Send and receive using only the `ffl` Python API -- both sides run in one
script, no browser involved. Shares a temporary file, downloads it back with
`ffl.download()`, and checks the round-tripped bytes match.

```bash
python examples/python_send_receive.py
```

## `selenium_receive_demo.py`

Sends with `ffl_demo.send()` (FastFileLink has no browser-based *upload* UI,
so sending is always initiated from the CLI/library), then **receives with a
real, Selenium-driven Chrome browser** -- opening the share link and letting
Chrome's own download manager save the file, exactly like a human recipient
would.

Requires:

```bash
pip install selenium
```

...and a local Chrome/Chromium install. Selenium Manager (bundled with
`selenium>=4.6`) fetches a matching `chromedriver` automatically -- no manual
driver setup needed.

```bash
python examples/selenium_receive_demo.py
python examples/selenium_receive_demo.py --no-headless   # watch it happen
```
