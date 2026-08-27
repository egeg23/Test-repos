--!strict
--- Passes, developer products and ad rewards.
---
--- Two lanes: pay, or watch ads and close most of the gap. The gap that stays
--- open is Economy.AdCatchUpTarget.
---
--- Rules that are platform policy rather than design preference are enforced in
--- code at the bottom of this file, because a rule living only in a comment is a
--- rule that gets broken during a late-night balance pass:
---   * an ad reward is a developer product, never Robux and never randomised;
---   * its value sits between 3 and 10 Robux equivalent;
---   * an ad is always a bonus, never a gate on progress;
---   * the reward is granted from ProcessReceipt after ShowAdResult.Succeeded,
---     never on the button press.

local Monetization = {}

export type Audience = "student" | "teacher"

export type Pass = {
	id: string,
	--- Filled in after the pass is created in the Creator Hub. Zero means unset,
	--- and PurchaseService refuses to sell it.
	gamePassId: number,
	robux: number,
	audience: Audience,
	displayKey: string,
}

export type Product = {
	id: string,
	devProductId: number,
	robux: number,
	audience: Audience,
	displayKey: string,
}

export type AdReward = {
	id: string,
	--- Ad rewards must be backed by a developer product: AdService builds the
	--- reward with CreateAdRewardFromDevProductId and the grant arrives through
	--- ProcessReceipt like any other purchase.
	devProductId: number,
	--- Robux-equivalent value of what the player receives. Policy band is 3..10.
	robuxEquivalent: number,
	cooldownSeconds: number,
	dailyLimit: number,
	--- For timed rewards, how long the effect lasts. The ratio of this to
	--- cooldownSeconds is what actually sets how far a free player can catch up,
	--- so it belongs in config next to the cooldown rather than buried in the
	--- service that applies it.
	boostSeconds: number?,
	audience: Audience,
	displayKey: string,
}

Monetization.Passes = {
	{ id = "xp2", gamePassId = 0, robux = 199, audience = "student", displayKey = "pass.xp2" },
	{ id = "hint", gamePassId = 0, robux = 149, audience = "student", displayKey = "pass.hint" },
	{
		id = "lessonSlots",
		gamePassId = 0,
		robux = 249,
		audience = "student",
		displayKey = "pass.lessonSlots",
	},
	{
		id = "autoNotes",
		gamePassId = 0,
		robux = 299,
		audience = "student",
		displayKey = "pass.autoNotes",
	},
	{
		id = "uniform",
		gamePassId = 0,
		robux = 99,
		audience = "student",
		displayKey = "pass.uniform",
	},
	{
		id = "classCapacity",
		gamePassId = 0,
		robux = 349,
		audience = "teacher",
		displayKey = "pass.classCapacity",
	},
	{
		id = "secondClass",
		gamePassId = 0,
		robux = 499,
		audience = "teacher",
		displayKey = "pass.secondClass",
	},
	{
		id = "listingPriority",
		gamePassId = 0,
		robux = 299,
		audience = "teacher",
		displayKey = "pass.listingPriority",
	},
	{
		id = "prefabPack",
		gamePassId = 0,
		robux = 249,
		audience = "teacher",
		displayKey = "pass.prefabPack",
	},
} :: { Pass }

Monetization.Products = {
	{
		id = "restoreAttempt",
		devProductId = 0,
		robux = 25,
		audience = "student",
		displayKey = "product.restoreAttempt",
	},
	{
		id = "xp3Boost",
		devProductId = 0,
		robux = 35,
		audience = "student",
		displayKey = "product.xp3Boost",
	},
	{
		id = "classPromoHour",
		devProductId = 0,
		robux = 49,
		audience = "teacher",
		displayKey = "product.classPromoHour",
	},
	{
		id = "extraTestSlot",
		devProductId = 0,
		robux = 35,
		audience = "teacher",
		displayKey = "product.extraTestSlot",
	},
} :: { Product }

--- Note what is absent: there is no product that sells the soft currency for
--- Robux. That is deliberate. The moment points are Robux-purchasable, every
--- random draw in the game falls under the paid random items policy, which means
--- published odds for every outcome and an under-18 ban in some markets. Selling
--- multipliers, capacity and time keeps the collection loop unregulated.
Monetization.AdRewards = {
	{
		id = "doubleLessonReward",
		devProductId = 0,
		robuxEquivalent = 8,
		cooldownSeconds = 1200,
		dailyLimit = 6,
		boostSeconds = 640,
		audience = "student",
		displayKey = "ad.doubleLessonReward",
	},
	{
		id = "extraAttempt",
		devProductId = 0,
		robuxEquivalent = 5,
		cooldownSeconds = 900,
		dailyLimit = 8,
		audience = "student",
		displayKey = "ad.extraAttempt",
	},
	{
		id = "skipCooldown",
		devProductId = 0,
		robuxEquivalent = 4,
		cooldownSeconds = 0,
		dailyLimit = 5,
		audience = "student",
		displayKey = "ad.skipCooldown",
	},
	{
		id = "doubleOfflineNotes",
		devProductId = 0,
		robuxEquivalent = 10,
		cooldownSeconds = 0,
		dailyLimit = 1,
		audience = "student",
		displayKey = "ad.doubleOfflineNotes",
	},
	{
		id = "doubleStreak",
		devProductId = 0,
		robuxEquivalent = 6,
		cooldownSeconds = 0,
		--- Once a day, because that is what it doubles. A second view would be
		--- doubling a thing already doubled, which is a different offer.
		dailyLimit = 1,
		audience = "student",
		displayKey = "ad.doubleStreak",
	},
	{
		id = "promoteClass",
		devProductId = 0,
		robuxEquivalent = 8,
		cooldownSeconds = 900,
		dailyLimit = 6,
		boostSeconds = 900,
		audience = "teacher",
		displayKey = "ad.promoteClass",
	},
	{
		id = "teacherTestSlot",
		devProductId = 0,
		robuxEquivalent = 6,
		cooldownSeconds = 0,
		dailyLimit = 1,
		audience = "teacher",
		displayKey = "ad.teacherTestSlot",
	},
} :: { AdReward }

Monetization.MinAdRewardRobux = 3
Monetization.MaxAdRewardRobux = 10

local passById: { [string]: Pass } = {}
for _, pass in Monetization.Passes do
	passById[pass.id] = pass
end

local productById: { [string]: Product } = {}
for _, product in Monetization.Products do
	productById[product.id] = product
end

local adRewardById: { [string]: AdReward } = {}
for _, reward in Monetization.AdRewards do
	assert(
		reward.robuxEquivalent >= Monetization.MinAdRewardRobux
			and reward.robuxEquivalent <= Monetization.MaxAdRewardRobux,
		`ad reward "{reward.id}" is worth {reward.robuxEquivalent} Robux, outside the 3..10 policy band`
	)
	assert(reward.dailyLimit > 0, `ad reward "{reward.id}" must have a positive daily limit`)
	adRewardById[reward.id] = reward
end

function Monetization.getPass(id: string): Pass?
	return passById[id]
end

function Monetization.getProduct(id: string): Product?
	return productById[id]
end

function Monetization.getAdReward(id: string): AdReward?
	return adRewardById[id]
end

--- Maps a developer product id back to whatever it funds. ProcessReceipt receives
--- a product id and nothing else, so this is how a receipt finds its grant.
function Monetization.resolveDevProduct(devProductId: number): (string?, string?)
	for _, product in Monetization.Products do
		if product.devProductId == devProductId and devProductId ~= 0 then
			return "product", product.id
		end
	end
	for _, reward in Monetization.AdRewards do
		if reward.devProductId == devProductId and devProductId ~= 0 then
			return "adReward", reward.id
		end
	end
	return nil, nil
end

return Monetization
