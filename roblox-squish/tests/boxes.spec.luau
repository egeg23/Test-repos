--!strict
local Boxes = require("../src/shared/Config/Boxes")
local Economy = require("../src/shared/Config/Economy")
local Squishes = require("../src/shared/Config/Squishes")
local Rng = require("./rng")
local t = require("./harness")

local function always(value: number): () -> number
	return function(): number
		return value
	end
end

return function()
	t.suite("Boxes: published odds")

	t.test("every box's odds add up to exactly 100%", function()
		for _, box in Boxes.List do
			local percent = 0
			for _, rarity in Squishes.RarityOrder do
				percent += Boxes.oddsPercent(box, rarity)
			end
			t.near(percent, 100, `{box.id} total`, 1e-9)
		end
	end)

	t.test("the roll lands on each rarity as often as the screen says", function()
		-- Pity is switched off by measuring only rolls the counter did not force:
		-- the counter is reset to zero before every roll.
		local rng = Rng.new(20261102)
		local rolls = 200000
		for _, box in Boxes.List do
			local counts: { [string]: number } = {}
			for _ = 1, rolls do
				local rarity = Boxes.rollRarity(box, 0, rng)
				counts[rarity] = (counts[rarity] or 0) + 1
			end
			for _, rarity in Squishes.RarityOrder do
				local expected = Boxes.oddsPercent(box, rarity) / 100
				local actual = (counts[rarity] or 0) / rolls
				-- Four standard errors, with a floor so a 0.2% bucket is not
				-- held to a tolerance tighter than its own noise.
				local tolerance = 4 * math.sqrt(math.max(expected, 0.001) * (1 - expected) / rolls)
				if math.abs(actual - expected) > tolerance then
					error(`{box.id}/{rarity}: shown {expected * 100}%, rolled {actual * 100}%`, 0)
				end
				if expected == 0 then
					t.equal(counts[rarity] or 0, 0, `{box.id} never rolls a 0% {rarity}`)
				end
			end
		end
	end)

	t.test("the pity promise is kept on exactly the box it names", function()
		for _, box in Boxes.List do
			local pity = box.pity
			if pity == nil then
				continue
			end
			-- rng = 0 always picks the lowest rarity the box can give, which is
			-- the unluckiest possible player.
			local counter = 0
			local landedAt = nil
			for boxNumber = 1, pity.within do
				local rarity, nextCounter = Boxes.rollRarity(box, counter, always(0))
				counter = nextCounter
				if Squishes.rarityRank(rarity) >= Squishes.rarityRank(pity.rarity) then
					landedAt = boxNumber
					break
				end
			end
			t.equal(landedAt, pity.within, `{box.id}: unluckiest player's guaranteed box`)
			t.equal(counter, 0, `{box.id}: counter resets after the guarantee`)
		end
	end)

	t.test("a lucky hit resets the pity counter", function()
		local box = Boxes.get("caramel")
		assert(box ~= nil)
		local rarity, counter = Boxes.rollRarity(box, 25, always(0.9999))
		t.equal(rarity, "legendary", "top of the caramel table")
		t.equal(counter, 0, "counter after a hit")
	end)

	t.test("boxes never hand out a seasonal squish", function()
		local rng = Rng.new(7)
		for _, rarity in Squishes.RarityOrder do
			if #Squishes.boxPool(rarity) == 0 then
				continue
			end
			for _ = 1, 500 do
				local species = Boxes.rollSpecies(rarity, rng)
				t.isTrue(species.season == nil, `{species.id} is not seasonal`)
				t.equal(species.rarity, rarity, "species matches rolled rarity")
			end
		end
	end)

	t.test("rollSpecies covers the whole pool", function()
		local seen: { [string]: boolean } = {}
		local rng = Rng.new(11)
		for _ = 1, 300 do
			seen[Boxes.rollSpecies("common", rng).id] = true
		end
		for _, species in Squishes.boxPool("common") do
			t.isTrue(seen[species.id] == true, `{species.id} can drop`)
		end
	end)

	t.test("no coin box can be resold for profit", function()
		-- If the expected resale of what a box gives beat its price, buying and
		-- selling boxes would be an infinite coin machine.
		for _, box in Boxes.List do
			local price = box.coins
			if price == nil then
				continue
			end
			local expected = 0
			for _, rarity in Squishes.RarityOrder do
				local share = Boxes.oddsPercent(box, rarity) / 100
				local value = Economy.incomePerSecond(rarity, 1) * Economy.ResaleSeconds
				expected += share * value
			end
			t.lessThan(expected, price, `{box.id} expected resale`)
		end
	end)

	t.test("exactly one box is sold for Robux, and it has a pity guarantee", function()
		local paid = 0
		for _, box in Boxes.List do
			if box.paid then
				paid += 1
				t.isTrue(box.pity ~= nil, `{box.id} has a guarantee`)
			end
		end
		t.equal(paid, 1, "paid boxes")
	end)
end
