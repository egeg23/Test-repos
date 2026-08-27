--!strict
--- Runs every spec under the standalone Luau binary.
---
--- Specs are listed rather than discovered: standalone Luau has no filesystem
--- listing, and an explicit list is one line to maintain and impossible to
--- silently skip.

local harness = require("./harness")

local specs = {
	require("./economy.spec"),
	require("./obstacles.spec"),
	require("./campus.spec"),
	require("./authoring.spec"),
	require("./progression.spec"),
	require("./strings.spec"),
	require("./decor.spec"),
	require("./achievements.spec"),
}

for _, spec in specs do
	spec()
end

local failed = harness.report()
if failed > 0 then
	error(`{failed} test(s) failed`, 0)
end
