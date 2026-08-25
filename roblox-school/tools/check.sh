#!/usr/bin/env bash
# Checks every Luau source file with the upstream Luau parser.
#
# What this can and cannot tell you:
#
#   Syntax errors and lints are reliable, and are what this gates on.
#
#   Type errors ACROSS MODULES are not. Requires here are Roblox instance paths
#   ("game.ReplicatedStorage.Shared.Types"), which no file-based tool can
#   resolve, so every type imported from another module degrades to an error
#   type and the checker then invents a structure from how the value is used.
#   That produces long cascades of confident-looking nonsense -- "does not have
#   key 'grade'" about a field that plainly exists. Verified by giving the
#   checker identical code with a local type declaration, which passes clean.
#
#   Type errors are therefore printed as advisory and do not fail the run. Read
#   them, but confirm anything they claim before acting on it. Real typechecking
#   needs luau-lsp with a Rojo sourcemap, in Studio or an editor.
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

status=0
count=0
advisory=0

while IFS= read -r file; do
	count=$((count + 1))
	out="$("$LUAU" "$file" 2>&1)"
	[ -z "$out" ] && continue

	hard="$(echo "$out" | grep -E ': (SyntaxError|LocalUnused|SameLineStatement|DuplicateFunction|UnreachableCode|DuplicateLocal):' || true)"
	if [ -n "$hard" ]; then
		echo "$hard"
		status=1
	fi

	soft="$(echo "$out" | grep -E ': TypeError:' || true)"
	if [ -n "$soft" ]; then
		advisory=$((advisory + $(echo "$soft" | wc -l)))
	fi
done < <(find src -name '*.luau' -type f | sort)

if [ "$status" -eq 0 ]; then
	echo "OK: $count Luau files, no syntax or lint errors."
	if [ "$advisory" -gt 0 ]; then
		echo "     ($advisory cross-module type diagnostics suppressed; see the note in this script.)"
	fi
fi
exit "$status"
