--!strict
--- Passes, developer products and ad rewards.
---
--- Rules that are platform policy rather than taste are asserted at the bottom
--- of this file, because a rule that lives only in a comment gets broken during
--- a late-night balance pass:
---
---   * the one random thing sold for Robux is the rainbow box, and it must point
---     at a box whose odds are published (Boxes asserts they sum to 100%);
---   * nothing sells coins for Robux. If coins could be bought, every coin box
---     would become a paid random item too, with all the rules that carries;
---   * an ad reward is a developer product worth 3..10 Robux, never random,
---     never a gate on progress, granted from ProcessReceipt only after the ad
---     reported success.
---
--- Ids are 0 until created in the Creator Hub. Zero means "not configured" and
--- the services refuse to sell it.

local Boxes = require(script.Parent.Boxes)

local Monetization = {}

export type Pass = {
	id: string,
	gamePassId: number,
	robux: number,
	--- Multiplies coins. Hidden from players restricted from paid random
	--- items: for them coins must never be bought with Robux, or the coin
	--- boxes would count as paid random items too.
	boostsCoins: boolean?,
}

export type Product = {
	id: string,
	devProductId: number,
	robux: number,
	--- Set when the product hands out a random result. Such a product must name
	--- a paid box, its odds are shown before purchase, and it is hidden from
	--- players PolicyService restricts paid random items for.
	paidBox: string?,
	boostSeconds: number?,
	shieldSeconds: number?,
	boostsCoins: boolean?,
}

export type AdReward = {
	id: string,
	devProductId: number,
	--- Robux-equivalent value of what the player receives. Policy band 3..10.
	robuxEquivalent: number,
	cooldownSeconds: number,
	dailyLimit: number,
	boostSeconds: number?,
	shieldSeconds: number?,
	--- For the coin gift: how many seconds of the player's current base income.
	incomeSeconds: number?,
}

Monetization.Passes = {
	{ id = "doubleCoins", gamePassId = 0, robux = 299, boostsCoins = true },
	{ id = "bigShelf", gamePassId = 0, robux = 149 },
	{ id = "comfyGloves", gamePassId = 0, robux = 99, boostsCoins = true },
} :: { Pass }

Monetization.Products = {
	{ id = "rainbowBox", devProductId = 0, robux = 49, paidBox = "rainbow" },
	{ id = "sugarRush", devProductId = 0, robux = 39, boostSeconds = 15 * 60, boostsCoins = true },
	{ id = "pillowFort", devProductId = 0, robux = 29, shieldSeconds = 60 * 60 },
} :: { Product }

Monetization.AdRewards = {
	{
		id = "adIncomeBoost",
		devProductId = 0,
		robuxEquivalent = 8,
		cooldownSeconds = 20 * 60,
		dailyLimit = 6,
		boostSeconds = 10 * 60,
	},
	{
		id = "adShield",
		devProductId = 0,
		robuxEquivalent = 5,
		cooldownSeconds = 30 * 60,
		dailyLimit = 3,
		shieldSeconds = 10 * 60,
	},
	{
		id = "adCoinGift",
		devProductId = 0,
		robuxEquivalent = 4,
		cooldownSeconds = 20 * 60,
		dailyLimit = 5,
		incomeSeconds = 3 * 60,
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
	local paidBox = product.paidBox
	if paidBox ~= nil then
		local box = Boxes.get(paidBox)
		assert(box ~= nil, `product "{product.id}" sells unknown box "{paidBox}"`)
		assert(box.paid, `product "{product.id}" sells coin box "{paidBox}" for Robux`)
	end
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

--- Maps a developer product id back to what it funds. ProcessReceipt receives
--- a product id and nothing else.
function Monetization.resolveDevProduct(devProductId: number): (string?, string?)
	if devProductId == 0 then
		return nil, nil
	end
	for _, product in Monetization.Products do
		if product.devProductId == devProductId then
			return "product", product.id
		end
	end
	for _, reward in Monetization.AdRewards do
		if reward.devProductId == devProductId then
			return "adReward", reward.id
		end
	end
	return nil, nil
end

return Monetization
