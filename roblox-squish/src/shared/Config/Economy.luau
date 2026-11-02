--!strict
--- Coins: what squishes earn, what squeezing adds, what merging and shelves cost.
---
--- Every number a balance pass would touch is here, and every formula is a pure
--- function, so the simulator in tools/ runs the game's own arithmetic rather
--- than a copy kept in step by hand.
---
--- Coins are earned only by squishes sitting on shelves, and counted only on the
--- server. Nothing a client sends is ever a coin amount.

local Types = require(script.Parent.Parent.Types)
local Squishes = require(script.Parent.Squishes)

local Economy = {}

--- How often the server pays shelves.
Economy.TickSeconds = 1

--- Each merge tier multiplies income by this. Above 2 on purpose: two tier-1
--- squishes earn 2, the merged tier-2 earns 2.5 and frees a shelf. Merging has
--- to be worth a slot, or nobody does it.
Economy.TierMultiplier = 2.5
Economy.MaxTier = 5

--- Shelves.
Economy.StartSlots = 6
Economy.MaxBoughtSlots = 8
--- The bigShelf pass adds these on top. The base layout has room for all of
--- them: StartSlots + MaxBoughtSlots + PassSlots == Base.SlotCount, which the
--- layout test asserts.
Economy.PassSlots = 4
Economy.SlotBaseCost = 250
Economy.SlotCostGrowth = 1.9

--- Squeezing: a tap on a squish pays this many seconds of its income, once per
--- cooldown per squish. An active player out-earns an idle one by roughly
--- SqueezeSeconds / SqueezeCooldown, which keeps idling viable and playing
--- better.
Economy.SqueezeSeconds = 4
Economy.SqueezeCooldown = 6
--- The gloves pass doubles what a squeeze pays, not how often.
Economy.GlovesSqueezeMultiplier = 2
--- Server-side ceiling on squeezes per second across all of a player's squishes,
--- so an autoclicker gains nothing over a quick hand.
Economy.MaxSqueezesPerSecond = 3

--- Multipliers. Additive, so a pass and an ad boost together make x3 rather
--- than x4: the ad lane closes a gap, it does not compound one.
Economy.PassIncomeBonus = 1
Economy.AdBoostIncomeBonus = 1
Economy.PaidBoostIncomeBonus = 2

--- Hard cap on squishes owned, shelved or pocketed. Profiles have a size limit
--- and a collection past this is better merged than stored.
Economy.MaxOwned = 80

--- A player's first squish is free and always the same common, so the very
--- first minute ends with something on a shelf to squeeze.
Economy.StarterSpecies = "dumpling"
Economy.StartCoins = 60

function Economy.incomePerSecond(rarity: Types.Rarity, tier: number): number
	local base = Squishes.Rarities[rarity].income
	return base * Economy.TierMultiplier ^ (tier - 1)
end

function Economy.squishIncome(squish: Types.Squish): number
	local species = Squishes.get(squish.species)
	if species == nil then
		return 0
	end
	return Economy.incomePerSecond(species.rarity, squish.tier)
end

export type Modifiers = {
	incomePass: boolean,
	adBoost: boolean,
	paidBoost: boolean,
}

function Economy.incomeMultiplier(mods: Modifiers): number
	local multiplier = 1
	if mods.incomePass then
		multiplier += Economy.PassIncomeBonus
	end
	if mods.adBoost then
		multiplier += Economy.AdBoostIncomeBonus
	end
	if mods.paidBoost then
		multiplier += Economy.PaidBoostIncomeBonus
	end
	return multiplier
end

function Economy.squeezeReward(income: number, gloves: boolean): number
	local reward = income * Economy.SqueezeSeconds
	if gloves then
		reward *= Economy.GlovesSqueezeMultiplier
	end
	return reward
end

function Economy.totalSlots(boughtSlots: number, hasPass: boolean): number
	return Economy.StartSlots + math.clamp(boughtSlots, 0, Economy.MaxBoughtSlots) + (if hasPass then Economy.PassSlots else 0)
end

--- Cost of the next bought slot, or nil when the bought ladder is complete.
function Economy.nextSlotCost(boughtSlots: number): number?
	if boughtSlots >= Economy.MaxBoughtSlots then
		return nil
	end
	return math.floor(Economy.SlotBaseCost * Economy.SlotCostGrowth ^ boughtSlots)
end

--- Two squishes merge when they are the same species at the same tier below the
--- cap. The result is one squish a tier up; both inputs are consumed.
function Economy.canMerge(a: Types.Squish, b: Types.Squish): (boolean, string?)
	if a.uid == b.uid then
		return false, "same"
	end
	if a.species ~= b.species then
		return false, "species"
	end
	if a.tier ~= b.tier then
		return false, "tier"
	end
	if a.tier >= Economy.MaxTier then
		return false, "maxTier"
	end
	return true, nil
end

--- Coins a player could get by selling a squish back to the factory: a few
--- minutes of its income. Exists so a duplicate with nowhere to go is still
--- worth something, and small enough that boxes are never a coin farm:
--- tests assert the expected resale of every coin box is below its price.
Economy.ResaleSeconds = 30

function Economy.resaleValue(squish: Types.Squish): number
	return math.floor(Economy.squishIncome(squish) * Economy.ResaleSeconds)
end

return Economy
