#!/usr/bin/env bash
# Everything that can be verified outside Roblox Studio.
set -uo pipefail
cd "$(dirname "$0")/.."

status=0
run() {
	echo
	echo "### $1"
	shift
	"$@" || status=1
}

run "Luau syntax and lints" ./tools/check.sh
run "Unit tests (odds, economy, theft rules, base layout, strings)" ./tools/test.sh
run "Circular requires" python3 tools/check_requires.py
run "Cross-module calls" python3 tools/check_calls.py
run "Hardcoded strings and string keys" python3 tools/check_hardcoded.py
run "Monetization and policy gates" python3 tools/check_monetization.py
run "Anti-cheat: coins and theft are server-side" python3 tools/check_anticheat.py
run "Economy simulation" ./tools/simulate_economy.sh

echo
if [ "$status" -eq 0 ]; then
	echo "All checks passed."
else
	echo "Some checks failed."
fi
exit "$status"
