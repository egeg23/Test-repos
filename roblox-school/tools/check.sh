#!/usr/bin/env bash
# Syntax-checks every Luau source file with the upstream Luau parser.
#
# Scope: this catches syntax errors and unused-local/shadowing lints. It does NOT
# typecheck against the Roblox API -- luau-lsp's globalTypes.d.luau uses
# `declare class ... with ... end`, which the upstream luau-analyze binary cannot
# parse. "Unknown global" diagnostics are therefore expected and filtered out.
set -uo pipefail
cd "$(dirname "$0")/.."

LUAU_DIR="${LUAU_DIR:-.luau-bin}"
LUAU="$LUAU_DIR/luau-analyze"

if [ ! -x "$LUAU" ]; then
	echo "luau-analyze not found, downloading into $LUAU_DIR ..."
	mkdir -p "$LUAU_DIR"
	curl -sSL -o "$LUAU_DIR/luau.zip" \
		"https://github.com/luau-lang/luau/releases/latest/download/luau-ubuntu.zip" || exit 1
	unzip -o -q "$LUAU_DIR/luau.zip" -d "$LUAU_DIR" || exit 1
	chmod +x "$LUAU_DIR"/luau* || exit 1
fi

# Diagnostics that are noise without Roblox API definitions.
IGNORE='Unknown global|Unknown require|Unknown type|Cannot find require path'

status=0
count=0
while IFS= read -r file; do
	count=$((count + 1))
	out="$("$LUAU" "$file" 2>&1 | grep -Ev "$IGNORE")"
	if [ -n "$out" ]; then
		echo "$out"
		status=1
	fi
done < <(find src -name '*.luau' -type f | sort)

if [ "$status" -eq 0 ]; then
	echo "OK: $count Luau files, no syntax errors."
fi
exit "$status"
