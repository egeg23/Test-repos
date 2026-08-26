#!/usr/bin/env bash
# Everything that can be checked outside Roblox Studio.
set -uo pipefail
cd "$(dirname "$0")/.."

status=0
run() {
	echo
	echo "### $1"
	shift
	"$@" || status=1
}

run "Luau syntax" ./tools/check.sh
run "Unit tests" ./tools/test.sh
run "Circular requires" python3 tools/check_requires.py
run "Question bank rules" python3 tools/validate_bank.py
run "Assembly tasks" python3 tools/validate_assembly.py
run "Obstacle difficulty" python3 tools/check_obstacles.py
run "Campus elections" python3 tools/check_campus.py
run "Economy simulation" python3 tools/simulate_economy.py

echo
if [ "$status" -eq 0 ]; then
	echo "All checks passed."
else
	echo "Some checks failed."
fi
exit "$status"
