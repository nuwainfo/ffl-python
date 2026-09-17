#!/usr/bin/env sh
set -eu
root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
exec apebind inspect "$1" --command-file "$root/binding/ffl.commands.yaml" --output "$root/binding/ffl.discovered.apebind.yaml"
