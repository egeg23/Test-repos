#!/usr/bin/env bash
# Mirrors the shared modules into .test-build with their requires rewritten.
#
# In the game, modules reach each other through Roblox instance paths:
# `require(script.Parent.Squishes)`. Standalone Luau has no `script`, so the
# tests and the simulator run against a copy where those two forms become file
# paths. Only the shared folder is mirrored: it is the part that imports nothing
# from the engine, and the part whose arithmetic the game actually runs.
#
# The rewrite is mechanical and refuses anything it does not recognise: a
# require of some other shape left in a shared module fails the build here
# instead of failing mysteriously inside a test.
set -euo pipefail
cd "$(dirname "$0")/.."

rm -rf .test-build
mkdir -p .test-build/src
cp -r src/shared .test-build/src/shared
# Render builds Instances; it is engine code and has no place in this build.
rm -rf .test-build/src/shared/Render
cp -r tests .test-build/tests
cp -r tools .test-build/tools

while IFS= read -r file; do
	sed -i -E \
		-e 's/require\(script\.Parent\.Parent\.([A-Za-z_]+)\)/require("..\/\1")/g' \
		-e 's/require\(script\.Parent\.([A-Za-z_]+)\)/require(".\/\1")/g' \
		"$file"
	if grep -nE 'require\((script|game|ReplicatedStorage)' "$file"; then
		echo "luau_build: $file has a require the standalone build cannot resolve" >&2
		exit 1
	fi
done < <(find .test-build/src/shared -name '*.luau')
