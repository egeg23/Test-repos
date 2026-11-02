--!strict
--- Rewarded video.
---
--- The order of operations in this file is policy, not style. Getting it wrong
--- risks ad payouts being revoked, so it is worth stating plainly:
---
---   1. PolicyService decides whether the player may be shown ads at all. Players
---      it says no to never see the button -- not a disabled button, no button.
---   2. Availability is checked as close to the show as possible; a stale check
---      means offering a reward that cannot be delivered.
---   3. The reward is a developer product, shown through ShowRewardedVideoAdAsync.
---   4. The player is credited from ProcessReceipt, and only after the ad
---      reported Succeeded. Crediting on the button press is a violation, not a
---      shortcut.
---
--- An ad is never a gate. Nothing in the game is unreachable without watching one;
--- every reward here is a bonus on top of a path that already works.

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RobloxAdService = game:GetService("AdService")

local Monetization = require(ReplicatedStorage.Shared.Config.Monetization)
local Remotes = require(ReplicatedStorage.Shared.Remotes)
local Types = require(ReplicatedStorage.Shared.Types)
local Analytics = require(script.Parent.AnalyticsService)
local DataService = require(script.Parent.DataService)
local PolicyCache = require(script.Parent.PolicyCache)
local PurchaseService = require(script.Parent.PurchaseService)
local RateLimiter = require(script.Parent.RateLimiter)
local SquishService = require(script.Parent.SquishService)

local AdService = {}

local SECONDS_PER_DAY = 86400
--- How long a watched ad stays claimed while its receipt is on the way.
local RECEIPT_GRACE_SECONDS = 60

--- Rewards currently being shown, so a client cannot open six ads at once and
--- have every one of them pass the cooldown check before any receipt lands.
local inFlight: { [Player]: { [string]: boolean } } = {}

local function dayStamp(): number
	return math.floor(os.time() / SECONDS_PER_DAY)
end

local function resetDailyIfNeeded(data: Types.ProfileData)
	local today = dayStamp()
	if data.adDayStamp ~= today then
		data.adDayStamp = today
		data.adDailyCounts = {}
	end
end

--- False whenever we are not certain: an unavailable policy service must not be
--- read as permission to show ads to a child. See PolicyCache.
function AdService.adsAllowed(player: Player): boolean
	return PolicyCache.adsAllowed(player)
end

function AdService.canWatch(player: Player, rewardId: string): (boolean, string?)
	local reward = Monetization.getAdReward(rewardId)
	if reward == nil then
		return false, "unknownReward"
	end
	if reward.devProductId == 0 then
		return false, "notConfigured"
	end
	if not AdService.adsAllowed(player) then
		return false, "policy"
	end

	local playerInFlight = inFlight[player]
	if playerInFlight ~= nil and playerInFlight[rewardId] then
		return false, "alreadyShowing"
	end

	local data = DataService.getData(player)
	if data == nil then
		return false, "notLoaded"
	end
	resetDailyIfNeeded(data)

	local used = data.adDailyCounts[rewardId] or 0
	if used >= reward.dailyLimit then
		return false, "dailyLimit"
	end

	if reward.cooldownSeconds > 0 then
		local last = data.adCooldowns[rewardId] or 0
		if os.time() - last < reward.cooldownSeconds then
			return false, "cooldown"
		end
	end

	return true, nil
end

--- What the player could watch right now, and why not where not. A player
--- PolicyService says no to gets an empty list: no button to draw at all.
function AdService.availability(player: Player): { any }
	local data = DataService.getData(player)
	if data == nil or not AdService.adsAllowed(player) then
		return {}
	end
	resetDailyIfNeeded(data)
	local now = os.time()
	local results: { any } = {}
	for _, reward in Monetization.AdRewards do
		local allowed, reason = AdService.canWatch(player, reward.id)
		local last: number = data.adCooldowns[reward.id] or 0
		table.insert(results, {
			id = reward.id,
			available = allowed,
			reason = reason,
			cooldownLeft = math.max(0, reward.cooldownSeconds - (now - last)),
			usedToday = data.adDailyCounts[reward.id] or 0,
			dailyLimit = reward.dailyLimit,
		})
	end
	return results
end

--- What each reward does. Nothing here is random and nothing grants Robux.
local effects: { [string]: (Player, Types.ProfileData) -> () } = {
	adIncomeBoost = function(_player, data)
		local reward = Monetization.getAdReward("adIncomeBoost") :: Monetization.AdReward
		local now = os.time()
		data.activeBoosts.ad = math.max(now, data.activeBoosts.ad or 0) + (reward.boostSeconds :: number)
	end,
	adShield = function(_player, data)
		local reward = Monetization.getAdReward("adShield") :: Monetization.AdReward
		data.shieldUntil = math.max(os.time(), data.shieldUntil) + (reward.shieldSeconds :: number)
	end,
	adCoinGift = function(player, data)
		local reward = Monetization.getAdReward("adCoinGift") :: Monetization.AdReward
		-- Base income, without multipliers: the gift is a fixed slice of what the
		-- shelves earn, not a way to double-dip on a pass or a boost.
		local amount = math.floor(SquishService.baseIncome(data) * (reward.incomeSeconds :: number))
		SquishService.addCoins(player, data, amount, "adGift")
	end,
}

local function setInFlight(player: Player, rewardId: string, value: boolean)
	local playerInFlight = inFlight[player]
	if playerInFlight == nil then
		if not value then
			return
		end
		playerInFlight = {}
		inFlight[player] = playerInFlight
	end
	playerInFlight[rewardId] = value or nil
end

--- Registered with PurchaseService, so an ad reward is credited through exactly
--- the same idempotent receipt path as a paid purchase. The cooldown and the
--- daily count are stamped here rather than when the ad started, because this is
--- the point at which we know the player actually watched it.
---
--- Clearing the in-flight mark is also this function's job. The mark cannot be
--- dropped when the video ends: the counters do not move until the receipt
--- arrives, so between those two moments a second request would find no cooldown
--- and no spent quota, and the daily limit would be whatever the player could
--- fit into that window.
local function grantAdReward(player: Player, data: Types.ProfileData, rewardId: string): boolean
	local effect = effects[rewardId]
	if effect == nil then
		return false
	end

	resetDailyIfNeeded(data)
	data.adCooldowns[rewardId] = os.time()
	data.adDailyCounts[rewardId] = (data.adDailyCounts[rewardId] or 0) + 1
	effect(player, data)
	setInFlight(player, rewardId, false)
	Analytics.adGranted(player, rewardId)
	task.defer(SquishService.push, player)
	return true
end


local function onRequestAd(player: Player, rewardId: unknown)
	if typeof(rewardId) ~= "string" then
		return
	end
	if not RateLimiter.consume(player, "RequestAd", 3, 0.2) then
		return
	end

	local adState = Remotes.event(Remotes.Names.AdState)
	local allowed, reason = AdService.canWatch(player, rewardId :: string)
	if not allowed then
		adState:FireClient(player, rewardId, false, reason)
		return
	end

	local reward = Monetization.getAdReward(rewardId :: string)
	if reward == nil then
		return
	end

	setInFlight(player, rewardId :: string, true)
	Analytics.adOffered(player, rewardId :: string)

	local ok, result = pcall(function()
		local adReward = RobloxAdService:CreateAdRewardFromDevProductId(reward.devProductId)
		return RobloxAdService:ShowRewardedVideoAdAsync(player, adReward)
	end)

	if not ok then
		setInFlight(player, rewardId :: string, false)
		warn(`rewarded video failed for {player.Name}/{rewardId}: {result}`)
		adState:FireClient(player, rewardId, false, "error")
		return
	end

	-- Succeeded only means the ad played to the end. The reward itself arrives
	-- through ProcessReceipt; the client is told so it can stop showing a spinner.
	local succeeded = result == Enum.ShowAdResult.Succeeded
	Analytics.adResult(player, rewardId :: string, succeeded)
	if not succeeded then
		setInFlight(player, rewardId :: string, false)
	else
		-- A receipt that never arrives would otherwise leave this reward blocked
		-- for the rest of the session. The window is long enough that a receipt
		-- in flight always wins the race.
		task.delay(RECEIPT_GRACE_SECONDS, function()
			setInFlight(player, rewardId :: string, false)
		end)
	end
	adState:FireClient(player, rewardId, succeeded, if succeeded then nil else tostring(result))
end

function AdService.start()
	for _, reward in Monetization.AdRewards do
		PurchaseService.registerGrant("adReward", reward.id, grantAdReward)
	end

	Remotes.event(Remotes.Names.RequestAd).OnServerEvent:Connect(onRequestAd)

	Players.PlayerRemoving:Connect(function(player: Player)
		inFlight[player] = nil
	end)
end

return AdService
