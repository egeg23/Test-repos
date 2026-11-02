#!/usr/bin/env bash
# Runs the economy simulation against the game's own modules and saves the
# numbers for the concept page.
set -uo pipefail
cd "$(dirname "$0")/.."
LUAU="${LUAU_DIR:-.luau-bin}/luau"
[ -x "$LUAU" ] || ./tools/test.sh >/dev/null
./tools/luau_build.sh || exit 1
out="$("$LUAU" -O2 --codegen .test-build/tools/simulate_economy.luau -a "$@" 2>&1)"
status=$?
echo "$out" | sed '/^REPORT$/,/^}$/d'
echo "$out" | sed -n '/^REPORT$/,/^}$/p' | sed '1d' > docs/economy.json
exit $status
