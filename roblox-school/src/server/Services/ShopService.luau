--!strict
--- Consumable purchases.
---
--- These register as grants on PurchaseService, so a bought product and a watched
--- ad arrive down exactly the same idempotent receipt path. There is deliberately
--- no product that sells the soft currency: the moment points can be bought with
--- Robux, every random draw in the game falls under the paid random items policy.

local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Monetization = require(ReplicatedStorage.Shared.Config.Monetization)
local Types = require(ReplicatedStorage.Shared.Types)
local PurchaseService = require(script.Parent.PurchaseService)

local ShopService = {}

local XP3_BOOST_SECONDS = 1200
local CLASS_PROMO_SECONDS = 3600

--- Same inversion as AdService: the shop grants a class promotion without
--- importing the class service that performs it.
local promoteClass: ((Player, number) -> ())? = nil

function ShopService.setClassPromoter(fn: (Player, number) -> ())
	promoteClass = fn
end

local function bump(map: { [string]: number }, key: string)
	local current: number = map[key] or 0
	map[key] = current + 1
end

local effects: { [string]: (Player, Types.ProfileData) -> () } = {
	restoreAttempt = function(_player, data)
		bump(data.consumables, "attempt")
	end,
	xp3Boost = function(_player, data)
		data.activeBoosts.lessonX3 = os.time() + XP3_BOOST_SECONDS
	end,
	classPromoHour = function(player, _data)
		local promote = promoteClass
		if promote ~= nil then
			task.spawn(promote, player, CLASS_PROMO_SECONDS)
		end
	end,
	extraTestSlot = function(_player, data)
		bump(data.consumables, "testSlot")
	end,
}

local function grantProduct(player: Player, data: Types.ProfileData, productId: string): boolean
	local effect = effects[productId]
	if effect == nil then
		return false
	end
	effect(player, data)
	return true
end

function ShopService.start()
	for _, product in Monetization.Products do
		if effects[product.id] ~= nil then
			PurchaseService.registerGrant("product", product.id, grantProduct)
		else
			warn(`ShopService: product "{product.id}" has no effect and cannot be sold`)
		end
	end
end

return ShopService
