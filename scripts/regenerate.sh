#!/usr/bin/env sh
set -eu

if [ "$#" -ne 1 ]; then
    echo "usage: $0 /path/to/ffl.com" >&2
    exit 2
fi

project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
temporary_root=$(mktemp -d "${TMPDIR:-/tmp}/ffl-python-generated.XXXXXX")
generated_package="$temporary_root/src/ffl"

cleanup() {
    rm -rf "$temporary_root"
}

trap cleanup EXIT HUP INT TERM

apebind generate "$project_root/binding/ffl.apebind.yaml" --ape "$1" --lang python --output "$temporary_root"

cp "$generated_package/_generated.py" "$project_root/src/ffl/_generated.py"
cp "$generated_package/_runtime.py" "$project_root/src/ffl/_runtime.py"
cp "$generated_package/py.typed" "$project_root/src/ffl/py.typed"
cp "$generated_package/bin/ffl.com" "$project_root/src/ffl/bin/ffl.com"
