#!/usr/bin/env bash
# Runs the Luau unit tests under the standalone Luau binary.
#
# These execute the real shared modules -- the odds, the economy, the theft
# rules, the base layout -- not a description of them. tools/luau_build.sh makes
# a copy whose instance-path requires are file paths; nothing else changes.
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

./tools/luau_build.sh || exit 1
exec "$LUAU" .test-build/tests/run.luau
