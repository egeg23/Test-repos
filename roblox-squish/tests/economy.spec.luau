--!strict
local Economy = require("../src/shared/Config/Economy")
local Squishes = require("../src/shared/Config/Squishes")
local t = require("./harness")

local function squish(uid: string, species: string, tier: number): any
	return { uid = uid, species = species, tier = tier, origin = "box", obtainedAt = 0 }
end

return function()
	t.suite("Economy: income and merging")

	t.test("rarer squishes always earn more", function()
		local previous = 0
		for _, rarity in Squishes.RarityOrder do
			local income = Economy.incomePerSecond(rarity, 1)
			t.greaterThan(income, previous, `{rarity} income`)
			previous = income
		end
	end)

	t.test("a merge is worth more than the two squishes it consumed", function()
		for _, rarity in Squishes.RarityOrder do
			for tier = 1, Economy.MaxTier - 1 do
				local pair = 2 * Economy.incomePerSecond(rarity, tier)
				local merged = Economy.incomePerSecond(rarity, tier + 1)
				t.greaterThan(merged, pair, `{rarity} tier {tier} merge`)
			end
		end
	end)

	t.test("only same species, same tier, below the cap merge", function()
		t.isTrue((Economy.canMerge(squish("a", "mochi", 1), squish("b", "mochi", 1))), "pair")
		t.isFalse((Economy.canMerge(squish("a", "mochi", 1), squish("a", "mochi", 1))), "itself")
		t.isFalse((Economy.canMerge(squish("a", "mochi", 1), squish("b", "toast", 1))), "species")
		t.isFalse((Economy.canMerge(squish("a", "mochi", 1), squish("b", "mochi", 2))), "tier")
		local cap = Economy.MaxTier
		t.isFalse((Economy.canMerge(squish("a", "mochi", cap), squish("b", "mochi", cap))), "cap")
	end)

	t.test("pass and ad boost add rather than multiply", function()
		t.equal(Economy.incomeMultiplier({ incomePass = false, adBoost = false, paidBoost = false }), 1, "none")
		t.equal(Economy.incomeMultiplier({ incomePass = true, adBoost = false, paidBoost = false }), 2, "pass")
		t.equal(Economy.incomeMultiplier({ incomePass = true, adBoost = true, paidBoost = false }), 3, "pass+ad")
	end)

	t.test("squeezing helps but never beats leaving a squish to earn", function()
		-- Squeezing one squish as fast as allowed adds SqueezeSeconds of income
		-- every SqueezeCooldown seconds. It must stay a bonus below 100%, so an
		-- idle player is behind an active one but not left behind.
		local bonus = Economy.SqueezeSeconds / Economy.SqueezeCooldown
		t.greaterThan(bonus, 0.25, "squeezing is worth doing")
		t.lessThan(bonus, 1, "squeezing does not dominate")
	end)

	t.test("shelf slots climb in price and stop at the cap", function()
		local previous = 0
		for bought = 0, Economy.MaxBoughtSlots - 1 do
			local cost = Economy.nextSlotCost(bought)
			assert(cost ~= nil)
			t.greaterThan(cost, previous, `slot {bought + 1}`)
			previous = cost
		end
		t.isTrue(Economy.nextSlotCost(Economy.MaxBoughtSlots) == nil, "no slot past the cap")
		t.equal(Economy.totalSlots(99, false), Economy.StartSlots + Economy.MaxBoughtSlots, "cap holds")
	end)

	t.test("the starter squish exists and is a common", function()
		local species = Squishes.get(Economy.StarterSpecies)
		assert(species ~= nil, "starter species exists")
		t.equal(species.rarity, "common", "starter rarity")
	end)
end
