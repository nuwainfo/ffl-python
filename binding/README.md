# Binding source

`ffl.apebind.yaml` is the reviewed semantic contract used to regenerate the low-level
Python binding. `ffl.commands.yaml` contains explicit hidden-command discovery seeds for
commands that FFL's root help does not enumerate.

The discovered CLI grammar and the semantic operation behavior are intentionally
separate. FFL-specific behavior belongs here or in the handwritten `src/ffl` semantic
layer, never in APEBind's generic help parser.


## Update workflow

`python scripts/inspect.py --ape /path/to/ffl.com` refreshes
`ffl.discovered.apebind.yaml` from the executable and the explicit seeds in
`ffl.commands.yaml`. Treat that file as discovery evidence only. Review its diff and
merge intentional changes into `ffl.apebind.yaml`, which remains the canonical semantic
contract used by `scripts/regenerate.py`.
