--!strict
--- Player profile storage.
---
--- ProfileStore rather than a bare DataStore, for session locking: without it two
--- servers can hold the same player's data at once, and every duplication bug in
--- a game with an economy starts there.

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local ProfileStore = require(ReplicatedStorage.Packages.ProfileStore)
local Types = require(ReplicatedStorage.Shared.Types)
local Locales = require(ReplicatedStorage.Shared.Config.Locales)

local DataService = {}

local SCHEMA_VERSION = 1
local STORE_NAME = "PlayerData_v1"
--- Played time feeds the anti-alt gate on teacher payouts, so it is accumulated
--- server-side on a tick rather than trusted from the client.
local PLAYTIME_TICK_SECONDS = 15

local TEMPLATE: Types.ProfileData = {
	schemaVersion = SCHEMA_VERSION,
	locale = Locales.Default,
	createdAt = 0,
	playSeconds = 0,
	points = 0,
	grade = 1,
	lessonsThisGrade = 0,
	graduatedCount = 0,
	awaitingGraduation = false,
	subjects = {},
	achievements = {},
	role = "student",
	teacher = {
		licensed = false,
		rank = "assistant",
		rating = 0,
		ratingCount = 0,
		classIds = {},
		pendingPayout = 0,
	},
	teacherHistory = {},
	grantedReceipts = {},
	adCooldowns = {},
	adDailyCounts = {},
	adDayStamp = 0,
	ownedPasses = {},
	activeBoosts = {},
	consumables = {},
}

local store = ProfileStore.New(STORE_NAME, TEMPLATE)

local profiles: { [Player]: any } = {}
local loadedEvent = Instance.new("BindableEvent")

DataService.ProfileLoaded = loadedEvent.Event

--- Returns the live profile, or nil when it is still loading or has been released.
--- Callers that grant anything must treat nil as "not yet", never as "empty".
function DataService.get(player: Player): any?
	return profiles[player]
end

function DataService.getData(player: Player): Types.ProfileData?
	local profile = profiles[player]
	if profile == nil or not profile:IsActive() then
		return nil
	end
	return profile.Data
end

--- Yields until the profile is available. Returns nil if it never arrives, which
--- happens when the player leaves during load.
function DataService.waitForData(player: Player, timeoutSeconds: number?): Types.ProfileData?
	local existing = DataService.getData(player)
	if existing ~= nil then
		return existing
	end

	local deadline = os.clock() + (timeoutSeconds or 20)
	while os.clock() < deadline do
		if player.Parent == nil then
			return nil
		end
		local data = DataService.getData(player)
		if data ~= nil then
			return data
		end
		task.wait(0.1)
	end
	return nil
end

local function onPlayerAdded(player: Player)
	local profile = store:StartSessionAsync(`{player.UserId}`, {
		Cancel = function()
			return player.Parent ~= Players
		end,
	})

	if profile == nil then
		-- Another server holds the session and would not release it. Kicking is
		-- the honest outcome: letting the player in with a blank profile would
		-- silently overwrite everything they own.
		player:Kick("Could not load your data. Please rejoin.")
		return
	end

	profile:AddUserId(player.UserId)
	profile:Reconcile()

	profile.OnSessionEnd:Connect(function()
		profiles[player] = nil
		player:Kick("Your data session ended. Please rejoin.")
	end)

	if player.Parent ~= Players then
		profile:EndSession()
		return
	end

	local data: Types.ProfileData = profile.Data
	if data.createdAt == 0 then
		data.createdAt = os.time()
	end
	data.locale = Locales.fromPlayerLocaleId(player.LocaleId)

	profiles[player] = profile
	loadedEvent:Fire(player, data)
end

local function onPlayerRemoving(player: Player)
	local profile = profiles[player]
	if profile ~= nil then
		profile:EndSession()
		profiles[player] = nil
	end
end

function DataService.start()
	for _, player in Players:GetPlayers() do
		task.spawn(onPlayerAdded, player)
	end
	Players.PlayerAdded:Connect(onPlayerAdded)
	Players.PlayerRemoving:Connect(onPlayerRemoving)

	task.spawn(function()
		while true do
			task.wait(PLAYTIME_TICK_SECONDS)
			for _, profile in profiles do
				if profile:IsActive() then
					profile.Data.playSeconds += PLAYTIME_TICK_SECONDS
				end
			end
		end
	end)
end

return DataService
