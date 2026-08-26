--!strict
--- A test harness small enough to read in one sitting.
---
--- Deliberately not TestEZ: these tests run under the standalone Luau binary
--- rather than inside Roblox, which is the whole point of them. The config
--- modules import nothing from the engine, so they can be executed directly --
--- meaning these assertions run the real functions the game runs, not a copy of
--- them kept in step by hand.

local Harness = {}

local failures: { string } = {}
local passed = 0
local currentSuite = ""

function Harness.suite(name: string)
	currentSuite = name
	print(`\n{name}`)
	print(string.rep("-", #name))
end

local function record(name: string, ok: boolean, detail: string?)
	if ok then
		passed += 1
		print(`  ok   {name}`)
	else
		local message = `{currentSuite} / {name}: {detail or "failed"}`
		table.insert(failures, message)
		print(`  FAIL {name} -- {detail or "failed"}`)
	end
end

function Harness.test(name: string, body: () -> ())
	local ok, err = pcall(body)
	record(name, ok, if ok then nil else tostring(err))
end

function Harness.equal(actual: any, expected: any, what: string)
	if actual ~= expected then
		error(`{what}: expected {tostring(expected)}, got {tostring(actual)}`, 0)
	end
end

--- Floating point comparisons need slack; the alternative is tests that fail on
--- an arithmetic reordering that changed nothing.
function Harness.near(actual: number, expected: number, what: string, tolerance: number?)
	local slack = tolerance or 1e-9
	if math.abs(actual - expected) > slack then
		error(`{what}: expected about {expected}, got {actual}`, 0)
	end
end

function Harness.isTrue(value: boolean, what: string)
	if value ~= true then
		error(`{what}: expected true`, 0)
	end
end

function Harness.isFalse(value: boolean, what: string)
	if value ~= false then
		error(`{what}: expected false`, 0)
	end
end

function Harness.lessThan(actual: number, limit: number, what: string)
	if not (actual < limit) then
		error(`{what}: expected less than {limit}, got {actual}`, 0)
	end
end

function Harness.greaterThan(actual: number, limit: number, what: string)
	if not (actual > limit) then
		error(`{what}: expected more than {limit}, got {actual}`, 0)
	end
end

function Harness.report(): number
	print(`\n{passed} passed, {#failures} failed`)
	for _, failure in failures do
		print(`  - {failure}`)
	end
	return #failures
end

return Harness
