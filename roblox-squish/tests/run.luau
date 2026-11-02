--!strict
--- Runs every spec under the standalone Luau binary.
---
--- Specs are listed rather than discovered: standalone Luau has no directory
--- listing, and an explicit list cannot silently skip one.

local harness = require("./harness")

local specs = {
	require("./strings.spec"),
	require("./boxes.spec"),
	require("./economy.spec"),
	require("./steal.spec"),
	require("./social.spec"),
	require("./base.spec"),
}

for _, spec in specs do
	spec()
end

local failed = harness.report()
if failed > 0 then
	error(`{failed} test(s) failed`, 0)
end
