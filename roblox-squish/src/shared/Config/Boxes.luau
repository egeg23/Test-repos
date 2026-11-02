--!strict
--- Blind boxes, their odds, and the roll.
---
--- Odds are integers in hundredths of a percent and must sum to exactly 10000.
--- Floats would let a table that "adds up to 100" drift by a rounding error,
--- and the number on the purchase screen has to be the number the roll uses --
--- for the Robux box that is Roblox policy on paid random items, and for every
--- box it is simply honest. The interface reads `oddsPercent` below, the roll
--- reads the same weights, and tests/boxes.spec.luau holds the two together.
---
--- The pity counter is part of the published odds, not a hidden mercy: the
--- screen says "an epic or better no later than the Nth box", and the roll
--- keeps that promise exactly.

local Types = require(script.Parent.Parent.Types)
local Squishes = require(script.Parent.Squishes)

local Boxes = {}

Boxes.TotalWeight = 10000

export type Box = {
	id: string,
	--- Coin price. Nil for a box sold only for Robux.
	coins: number?,
	--- Set on the box a developer product sells. Monetization refers to it, and
	--- the box is hidden from anyone PolicyService restricts paid random items for.
	paid: boolean,
	odds: { [Types.Rarity]: number },
	pity: { rarity: Types.Rarity, within: number }?,
	colour: { number },
}

Boxes.List = {
	{
		id = "caramel",
		coins = 100,
		paid = false,
		odds = { common = 7900, rare = 1790, epic = 300, legendary = 10, mythic = 0 },
		pity = { rarity = "epic", within = 30 },
		colour = { 255, 214, 170 },
	},
	{
		id = "cloud",
		coins = 9000,
		paid = false,
		odds = { common = 5000, rare = 3700, epic = 1100, legendary = 195, mythic = 5 },
		pity = { rarity = "epic", within = 10 },
		colour = { 190, 226, 255 },
	},
	{
		id = "star",
		coins = 400000,
		paid = false,
		odds = { common = 1500, rare = 4500, epic = 3100, legendary = 865, mythic = 35 },
		pity = { rarity = "legendary", within = 15 },
		colour = { 255, 236, 160 },
	},
	{
		id = "rainbow",
		coins = nil,
		paid = true,
		odds = { common = 0, rare = 5500, epic = 3500, legendary = 900, mythic = 100 },
		pity = { rarity = "legendary", within = 10 },
		colour = { 255, 190, 230 },
	},
} :: { Box }

local byId: { [string]: Box } = {}
for _, box in Boxes.List do
	local total = 0
	for _, rarity in Squishes.RarityOrder do
		local weight = box.odds[rarity]
		assert(weight ~= nil and weight >= 0 and weight % 1 == 0, `box "{box.id}" has a bad weight for {rarity}`)
		if weight > 0 then
			assert(#Squishes.boxPool(rarity) > 0, `box "{box.id}" can roll {rarity}, which has no species`)
		end
		total += weight
	end
	assert(total == Boxes.TotalWeight, `box "{box.id}" odds sum to {total}, not {Boxes.TotalWeight}`)
	assert(box.paid == (box.coins == nil), `box "{box.id}" must be either coin-priced or paid, not both`)
	byId[box.id] = box
end

function Boxes.get(id: string): Box?
	return byId[id]
end

--- Percent for display, e.g. 2.7 for 270. The interface formats this and
--- nothing else, so a typo in the screen cannot disagree with the roll.
function Boxes.oddsPercent(box: Box, rarity: Types.Rarity): number
	return box.odds[rarity] / (Boxes.TotalWeight / 100)
end

--- True when a rarity is at or above the pity threshold.
local function meetsPity(box: Box, rarity: Types.Rarity): boolean
	local pity = box.pity
	if pity == nil then
		return false
	end
	return Squishes.rarityRank(rarity) >= Squishes.rarityRank(pity.rarity)
end

--- Rolls a rarity.
---
--- `sinceLast` is how many boxes of this type have been opened since the last
--- result that met the pity threshold. `rng` returns a float in [0, 1): passing
--- it in is what lets the tests and the simulator drive the real roll.
---
--- Returns the rarity and the new counter value.
function Boxes.rollRarity(box: Box, sinceLast: number, rng: () -> number): (Types.Rarity, number)
	local pity = box.pity
	local forced = pity ~= nil and sinceLast + 1 >= pity.within

	local total = 0
	for _, rarity in Squishes.RarityOrder do
		if not forced or meetsPity(box, rarity) then
			total += box.odds[rarity]
		end
	end

	local pick = rng() * total
	local result: Types.Rarity = Squishes.RarityOrder[1]
	local running = 0
	for _, rarity in Squishes.RarityOrder do
		if not forced or meetsPity(box, rarity) then
			local weight = box.odds[rarity]
			if weight > 0 then
				running += weight
				result = rarity
				if pick < running then
					break
				end
			end
		end
	end

	local nextCount = if meetsPity(box, result) then 0 else sinceLast + 1
	return result, nextCount
end

--- Picks a species of the rolled rarity, uniformly.
function Boxes.rollSpecies(rarity: Types.Rarity, rng: () -> number): Squishes.Species
	local pool = Squishes.boxPool(rarity)
	local index = math.clamp(math.floor(rng() * #pool) + 1, 1, #pool)
	return pool[index]
end

--- The chance that one box meets the pity threshold before pity is counted,
--- as a fraction. The simulator and the odds panel both use it.
function Boxes.pityRarityChance(box: Box): number
	local share = 0
	for _, rarity in Squishes.RarityOrder do
		if meetsPity(box, rarity) then
			share += box.odds[rarity]
		end
	end
	return share / Boxes.TotalWeight
end

return Boxes
