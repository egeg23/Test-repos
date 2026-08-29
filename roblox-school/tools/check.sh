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
#
# Unknown globals ARE gated, despite arriving as TypeError. A call to a function
# that does not exist is not a cross-module typing artefact -- it is a name that
# resolves to nil at run time -- and the whole reason the rest of TypeError is
# advisory does not apply to it. This gate was added after finding that
# LessonService had lost five requires and three definitions, including the one
# that supplies a lesson when a player walks up to a teacher and presses E. The
# game's main entry point had been broken for eighteen commits, and every other
# check in this repository passed the whole time.
#
# Roblox's own globals are not declared in any file, so they are allowed by name.
#
# tests/ is scanned alongside src/. It was not, once, and a syntax error sat in a
# spec file unreported -- Luau's require returns the compile error as a *string*
# rather than raising, so the runner failed with "attempt to call a string value"
# and said nothing about where or why.
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

# Names Roblox provides at run time and no file declares. Anything outside this
# list that the checker cannot see is a real missing definition.
ROBLOX_GLOBALS='game|script|workspace|shared|plugin|settings|Enum|Instance|Vector2|Vector3|CFrame|Color3|UDim|UDim2|NumberRange|NumberSequence|NumberSequenceKeypoint|ColorSequence|ColorSequenceKeypoint|Random|TweenInfo|BrickColor|Ray|Region3|DateTime|task|typeof|tick|time|delay|spawn|wait|elapsedTime|warn|require|utf8|bit32|buffer|vector|os|debug'

status=0
count=0
advisory=0

while IFS= read -r file; do
	count=$((count + 1))
	out="$("$LUAU" "$file" 2>&1)"
	[ -z "$out" ] && continue

	hard="$(echo "$out" | grep -E ': (SyntaxError|LocalUnused|ImportUnused|SameLineStatement|DuplicateFunction|UnreachableCode|DuplicateLocal|LocalShadow):' || true)"
	unknown="$(echo "$out" | grep "TypeError: Unknown global" \
		| grep -vE "Unknown global '($ROBLOX_GLOBALS)'" || true)"
	if [ -n "$unknown" ]; then
		echo "$unknown"
		status=1
	fi
	if [ -n "$hard" ]; then
		echo "$hard"
		status=1
	fi

	soft="$(echo "$out" | grep -E ': TypeError:' || true)"
	if [ -n "$soft" ]; then
		advisory=$((advisory + $(echo "$soft" | wc -l)))
	fi
done < <(find src tests -name '*.luau' -type f | sort)

if [ "$status" -eq 0 ]; then
	echo "OK: $count Luau files, no syntax or lint errors."
	if [ "$advisory" -gt 0 ]; then
		echo "     ($advisory cross-module type diagnostics suppressed; see the note in this script.)"
	fi
fi
exit "$status"
