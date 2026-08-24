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
local PolicyService = game:GetService("PolicyService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RobloxAdService = game:GetService("AdService")

local Monetization = require(ReplicatedStorage.Shared.Config.Monetization)
local Remotes = require(ReplicatedStorage.Shared.Remotes)
local Types = require(ReplicatedStorage.Shared.Types)
local DataService = require(script.Parent.DataService)
local PurchaseService = require(script.Parent.PurchaseService)
local RateLimiter = require(script.Parent.RateLimiter)

local AdService = {}

local SECONDS_PER_DAY = 86400

--- Cached per player: the policy call is a web request and the answer does not
--- change within a session.
local adsAllowedCache: { [Player]: boolean } = {}

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
--- read as permission to show ads to a child.
function AdService.adsAllowed(player: Player): boolean
	local cached = adsAllowedCache[player]
	if cached ~= nil then
		return cached
	end

	local ok, info = pcall(function()
		return PolicyService:GetPolicyInfoForPlayerAsync(player)
	end)

	local allowed = false
	if ok and typeof(info) == "table" then
		allowed = (info :: any).AreAdsAllowed == true
	end
	adsAllowedCache[player] = allowed
	return allowed
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

local function boostSeconds(rewardId: string): number
	local reward = Monetization.getAdReward(rewardId)
	return if reward ~= nil and reward.boostSeconds ~= nil then reward.boostSeconds else 0
end

local function bump(map: { [string]: number }, key: string)
	local current: number = map[key] or 0
	map[key] = current + 1
end

--- What each reward actually does. Timed effects go into activeBoosts, charges
--- into consumables. Nothing here grants Robux or currency directly.
local effects: { [string]: (Types.ProfileData) -> () } = {
	doubleLessonReward = function(data)
		data.activeBoosts.lessonX2 = os.time() + boostSeconds("doubleLessonReward")
	end,
	extraAttempt = function(data)
		bump(data.consumables, "attempt")
	end,
	skipCooldown = function(data)
		bump(data.consumables, "cooldownSkip")
	end,
	doubleOfflineNotes = function(data)
		bump(data.consumables, "offlineX2")
	end,
	promoteClass = function(data)
		data.activeBoosts.classPromo = os.time() + boostSeconds("promoteClass")
	end,
	teacherTestSlot = function(data)
		bump(data.consumables, "testSlot")
	end,
}

--- Registered with PurchaseService, so an ad reward is credited through exactly
--- the same idempotent receipt path as a paid purchase. The cooldown and the
--- daily count are stamped here rather than when the ad started, because this is
--- the point at which we know the player actually watched it.
local function grantAdReward(player: Player, data: Types.ProfileData, rewardId: string): boolean
	local effect = effects[rewardId]
	if effect == nil then
		return false
	end

	resetDailyIfNeeded(data)
	data.adCooldowns[rewardId] = os.time()
	bump(data.adDailyCounts, rewardId)
	effect(data)
	return true
end

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

	local ok, result = pcall(function()
		local adReward = RobloxAdService:CreateAdRewardFromDevProductId(reward.devProductId)
		return RobloxAdService:ShowRewardedVideoAdAsync(player, adReward)
	end)

	setInFlight(player, rewardId :: string, false)

	if not ok then
		warn(`rewarded video failed for {player.Name}/{rewardId}: {result}`)
		adState:FireClient(player, rewardId, false, "error")
		return
	end

	-- Succeeded only means the ad played to the end. The reward itself arrives
	-- through ProcessReceipt; the client is told so it can stop showing a spinner.
	local succeeded = result == Enum.ShowAdResult.Succeeded
	adState:FireClient(player, rewardId, succeeded, if succeeded then nil else tostring(result))
end

function AdService.start()
	for _, reward in Monetization.AdRewards do
		PurchaseService.registerGrant("adReward", reward.id, grantAdReward)
	end

	Remotes.event(Remotes.Names.RequestAd).OnServerEvent:Connect(onRequestAd)

	Players.PlayerRemoving:Connect(function(player: Player)
		adsAllowedCache[player] = nil
		inFlight[player] = nil
	end)
end

return AdService
