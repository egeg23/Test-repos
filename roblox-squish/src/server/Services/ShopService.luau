--!strict
--- The shop: what is for sale, prompting a purchase, and granting products.
---
--- The server prompts every purchase itself, after checking two things the
--- client cannot be trusted with: that the item is configured (its id is not
--- 0), and for the rainbow box, that PolicyService allows this player paid
--- random items. A restricted player is never shown the box, and if a purchase
--- still reaches ProcessReceipt for them -- a modified client can prompt on
--- its own -- the grant refuses, so Roblox refunds it rather than us selling a
--- random item where that is not allowed.

local MarketplaceService = game:GetService("MarketplaceService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Monetization = require(ReplicatedStorage.Shared.Config.Monetization)
local Remotes = require(ReplicatedStorage.Shared.Remotes)
local Types = require(ReplicatedStorage.Shared.Types)
local AdService = require(script.Parent.AdService)
local BoxService = require(script.Parent.BoxService)
local DataService = require(script.Parent.DataService)
local PolicyCache = require(script.Parent.PolicyCache)
local PurchaseService = require(script.Parent.PurchaseService)
local RateLimiter = require(script.Parent.RateLimiter)
local SquishService = require(script.Parent.SquishService)

local ShopService = {}

local function grantProduct(player: Player, data: Types.ProfileData, productId: string): boolean
	local product = Monetization.getProduct(productId)
	if product == nil then
		return false
	end
	local now = os.time()
	if product.paidBox ~= nil then
		if not PolicyCache.paidRandomAllowed(player) then
			return false
		end
		return BoxService.grantPaid(player, data, product.paidBox)
	elseif product.boostSeconds ~= nil then
		data.activeBoosts.paid = math.max(now, data.activeBoosts.paid or 0) + product.boostSeconds
	elseif product.shieldSeconds ~= nil then
		data.shieldUntil = math.max(now, data.shieldUntil) + product.shieldSeconds
	else
		return false
	end
	task.defer(SquishService.push, player)
	return true
end

--- Everything the shop panel draws for this player.
local function catalogue(player: Player): { [string]: any }
	local paidRandom = PolicyCache.paidRandomAllowed(player)
	local passes = {}
	for _, pass in Monetization.Passes do
		local owned = PurchaseService.ownsPass(player, pass.id)
		if pass.boostsCoins and not paidRandom and not owned then
			continue
		end
		table.insert(passes, {
			id = pass.id,
			robux = pass.robux,
			configured = pass.gamePassId ~= 0,
			owned = owned,
		})
	end
	local products = {}
	for _, product in Monetization.Products do
		-- Not "disabled" for a restricted player: absent.
		if (product.paidBox == nil and not product.boostsCoins) or paidRandom then
			table.insert(products, {
				id = product.id,
				robux = product.robux,
				configured = product.devProductId ~= 0,
				paidBox = product.paidBox,
			})
		end
	end
	return {
		passes = passes,
		products = products,
		ads = AdService.availability(player),
		paidRandomAllowed = paidRandom,
	}
end

local function onPromptPurchase(player: Player, kind: unknown, id: unknown)
	if typeof(kind) ~= "string" or typeof(id) ~= "string" then
		return
	end
	if not RateLimiter.consume(player, "PromptPurchase", 3, 0.5) then
		return
	end
	if kind == "pass" then
		local pass = Monetization.getPass(id :: string)
		if pass ~= nil and pass.boostsCoins and not PolicyCache.paidRandomAllowed(player) then
			return
		end
		if pass ~= nil and pass.gamePassId ~= 0 and not PurchaseService.ownsPass(player, pass.id) then
			MarketplaceService:PromptGamePassPurchase(player, pass.gamePassId)
		end
	elseif kind == "product" then
		local product = Monetization.getProduct(id :: string)
		if product == nil or product.devProductId == 0 then
			return
		end
		if (product.paidBox ~= nil or product.boostsCoins) and not PolicyCache.paidRandomAllowed(player) then
			return
		end
		MarketplaceService:PromptProductPurchase(player, product.devProductId)
	end
end

function ShopService.start()
	for _, product in Monetization.Products do
		PurchaseService.registerGrant("product", product.id, grantProduct)
	end
	Remotes.event(Remotes.Names.PromptPurchase).OnServerEvent:Connect(onPromptPurchase)
	Remotes.func(Remotes.Names.GetShop).OnServerInvoke = function(player: Player)
		if not RateLimiter.consume(player, "GetShop", 4, 1) then
			return nil
		end
		if DataService.getData(player) == nil then
			return nil
		end
		return catalogue(player)
	end
	-- A pass bought mid-session changes income and shelves at once.
	MarketplaceService.PromptGamePassPurchaseFinished:Connect(function(player: Player, _id: number, purchased: boolean)
		if purchased then
			task.delay(0.5, SquishService.refresh, player)
		end
	end)
end

return ShopService
