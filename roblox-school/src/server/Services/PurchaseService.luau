--!strict
--- Developer product and game pass purchases.
---
--- ProcessReceipt is called again whenever a grant is not acknowledged -- a
--- server crash, a network hiccup, a shutdown mid-grant. Without a record of what
--- has already been honoured, every one of those retries hands out the purchase a
--- second time. The receipt log in the profile is that record, and it is the
--- reason this file is small and fussy.

local MarketplaceService = game:GetService("MarketplaceService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Monetization = require(ReplicatedStorage.Shared.Config.Monetization)
local Types = require(ReplicatedStorage.Shared.Types)
local DataService = require(script.Parent.DataService)

local PurchaseService = {}

--- Roblox retries an unacknowledged receipt for a bounded window, so the log does
--- not need to be permanent -- but it must comfortably outlive that window.
local RECEIPT_RETENTION_SECONDS = 30 * 24 * 60 * 60
local RECEIPT_MAX_ENTRIES = 200

export type GrantFn = (player: Player, data: Types.ProfileData, id: string) -> boolean

local grants: { [string]: GrantFn } = {}

--- Remembers that a player does *not* own a pass, which the profile cannot: it
--- records ownership, so without this every lesson a non-owner finishes costs a
--- UserOwnsGamePassAsync web call. A purchase during the session clears the entry
--- through PromptGamePassPurchaseFinished, and the short expiry covers a purchase
--- made anywhere else.
local NEGATIVE_CACHE_SECONDS = 120
local unowned: { [Player]: { [string]: number } } = {}

local function grantKey(kind: string, id: string): string
	return `{kind}:{id}`
end

--- Services own their own grants: AdService registers the ad rewards, the shop
--- registers consumables. PurchaseService only decides whether a grant may run.
function PurchaseService.registerGrant(kind: string, id: string, fn: GrantFn)
	local key = grantKey(kind, id)
	assert(grants[key] == nil, `duplicate grant registered for {key}`)
	grants[key] = fn
end

local function pruneReceipts(data: Types.ProfileData)
	local now = os.time()
	local granted = data.grantedReceipts
	local keys: { string } = {}

	for receiptId, stamp in granted do
		if now - stamp > RECEIPT_RETENTION_SECONDS then
			granted[receiptId] = nil
		else
			table.insert(keys, receiptId)
		end
	end

	if #keys <= RECEIPT_MAX_ENTRIES then
		return
	end

	-- Oldest first, so the entries dropped are the ones least likely to still be
	-- inside Roblox's retry window.
	table.sort(keys, function(a, b)
		return granted[a] < granted[b]
	end)

	for index = 1, #keys - RECEIPT_MAX_ENTRIES do
		granted[keys[index]] = nil
	end
end

local function processReceipt(receiptInfo: any): Enum.ProductPurchaseDecision
	local player = Players:GetPlayerByUserId(receiptInfo.PlayerId)
	if player == nil then
		return Enum.ProductPurchaseDecision.NotProcessedYet
	end

	-- A profile that has not loaded is not an empty profile. Granting here would
	-- write the reward into a template that is about to be replaced by the real
	-- data, losing the purchase; NotProcessedYet asks Roblox to come back.
	local data = DataService.getData(player)
	if data == nil then
		return Enum.ProductPurchaseDecision.NotProcessedYet
	end

	local receiptId = tostring(receiptInfo.PurchaseId)
	if data.grantedReceipts[receiptId] ~= nil then
		-- Already honoured. Acknowledge so Roblox stops retrying, and grant nothing.
		return Enum.ProductPurchaseDecision.PurchaseGranted
	end

	local kind, id = Monetization.resolveDevProduct(receiptInfo.ProductId)
	if kind == nil or id == nil then
		return Enum.ProductPurchaseDecision.NotProcessedYet
	end

	local fn = grants[grantKey(kind, id)]
	if fn == nil then
		return Enum.ProductPurchaseDecision.NotProcessedYet
	end

	local ok, granted = pcall(fn, player, data, id)
	if not ok then
		warn(`grant for {kind}:{id} errored: {granted}`)
		return Enum.ProductPurchaseDecision.NotProcessedYet
	end
	if granted ~= true then
		return Enum.ProductPurchaseDecision.NotProcessedYet
	end

	data.grantedReceipts[receiptId] = os.time()
	pruneReceipts(data)

	-- Force the write before acknowledging. Relying on the autosave would leave a
	-- window where Roblox has been told the purchase is done but the profile does
	-- not yet know it, and a crash in that window loses the player's money.
	local profile = DataService.get(player)
	if profile ~= nil and profile:IsActive() then
		local saved = pcall(function()
			profile:Save()
		end)
		if not saved then
			return Enum.ProductPurchaseDecision.NotProcessedYet
		end
	end

	return Enum.ProductPurchaseDecision.PurchaseGranted
end

--- Exposed for tests: the same decision logic without touching MarketplaceService.
PurchaseService.processReceipt = processReceipt

function PurchaseService.ownsPass(player: Player, passId: string): boolean
	local data = DataService.getData(player)
	if data == nil then
		return false
	end
	if data.ownedPasses[passId] then
		return true
	end

	local pass = Monetization.getPass(passId)
	if pass == nil or pass.gamePassId == 0 then
		return false
	end

	local misses = unowned[player]
	if misses ~= nil then
		local checkedAt = misses[passId]
		if checkedAt ~= nil and os.clock() - checkedAt < NEGATIVE_CACHE_SECONDS then
			return false
		end
	end

	local ok, owns = pcall(function()
		return MarketplaceService:UserOwnsGamePassAsync(player.UserId, pass.gamePassId)
	end)
	if ok and owns then
		data.ownedPasses[passId] = true
		if misses ~= nil then
			misses[passId] = nil
		end
		return true
	end

	if ok then
		if misses == nil then
			misses = {}
			unowned[player] = misses
		end
		misses[passId] = os.clock()
	end
	return false
end

function PurchaseService.start()
	MarketplaceService.ProcessReceipt = processReceipt

	Players.PlayerRemoving:Connect(function(player: Player)
		unowned[player] = nil
	end)

	MarketplaceService.PromptGamePassPurchaseFinished:Connect(
		function(player: Player, gamePassId: number, wasPurchased: boolean)
			if not wasPurchased then
				return
			end
			local data = DataService.getData(player)
			if data == nil then
				return
			end
			for _, pass in Monetization.Passes do
				if pass.gamePassId == gamePassId then
					data.ownedPasses[pass.id] = true
					local misses = unowned[player]
					if misses ~= nil then
						misses[pass.id] = nil
					end
					break
				end
			end
		end
	)
end

return PurchaseService
