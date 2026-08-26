#!/usr/bin/env bash
# Runs the Luau unit tests under the standalone Luau binary.
#
# These execute the real config modules rather than a description of them. That
# is possible because those modules import nothing from the Roblox engine -- and
# it is why they are worth more than the Python checks alongside them, which can
# only read constants out of the source and reason about them.
set -uo pipefail
cd "$(dirname "$0")/.."

LUAU_DIR="${LUAU_DIR:-.luau-bin}"
LUAU="$LUAU_DIR/luau"

if [ ! -x "$LUAU" ]; then
	echo "luau not found, downloading into $LUAU_DIR ..."
	mkdir -p "$LUAU_DIR"
	curl -sSL -o "$LUAU_DIR/luau.zip" \
		"https://github.com/luau-lang/luau/releases/latest/download/luau-ubuntu.zip" || exit 1
	unzip -o -q "$LUAU_DIR/luau.zip" -d "$LUAU_DIR" || exit 1
	chmod +x "$LUAU_DIR"/luau* || exit 1
fi

exec "$LUAU" tests/run.luau
