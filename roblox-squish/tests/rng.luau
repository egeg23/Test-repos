--!strict
--- A seeded generator for the tests and the simulator, so a failing run can be
--- replayed exactly. Park-Miller: small, fast and good enough for odds checks.

local Rng = {}

function Rng.new(seed: number): () -> number
	local state = seed % 2147483647
	if state <= 0 then
		state += 2147483646
	end
	return function(): number
		state = (state * 48271) % 2147483647
		return (state - 1) / 2147483646
	end
end

return Rng
