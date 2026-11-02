--!strict
--- The weekly Squish Show.
---
--- Each player's score goes into an OrderedDataStore for the current week.
--- When a player joins after a week has closed, the server checks whether they
--- placed in that week's top and, if so, gives the season's squish and the
--- badge. Checking on join rather than at the week boundary means no server
--- has to be awake at midnight on Sunday for prizes to arrive.

local BadgeService = game:GetService("BadgeService")
local DataStoreService = game:GetService("DataStoreService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Badges = require(ReplicatedStorage.Shared.Config.Badges)
local Remotes = require(ReplicatedStorage.Shared.Remotes)
local Show = require(ReplicatedStorage.Shared.Config.Show)
local Squishes = require(ReplicatedStorage.Shared.Config.Squishes)
local Types = require(ReplicatedStorage.Shared.Types)
local DataService = require(script.Parent.DataService)
local RateLimiter = require(script.Parent.RateLimiter)
local SquishService = require(script.Parent.SquishService)

local ShowService = {}

--- Scores are written at most this often per player. Ordered stores have a
--- tight write budget and the board does not need to be live to the second.
local WRITE_INTERVAL = 300
local BOARD_CACHE_SECONDS = 120

local lastWrite: { [Player]: number } = {}
local boardCache: { week: number, at: number, rows: { any } }? = nil
local nameCache: { [number]: string } = {}

local function store(week: number): OrderedDataStore
	return DataStoreService:GetOrderedDataStore(`SquishShow_W{week}`)
end

local function writeScore(player: Player, data: Types.ProfileData, force: boolean)
	local now = os.clock()
	if not force and now - (lastWrite[player] or -math.huge) < WRITE_INTERVAL then
		return
	end
	lastWrite[player] = now
	local score = Show.score(data.squishes)
	if score <= 0 then
		return
	end
	local week = Show.weekIndex(os.time())
	task.spawn(function()
		pcall(function()
			store(week):SetAsync(tostring(player.UserId), score)
		end)
	end)
end

local function nameOf(userId: number): string
	local cached = nameCache[userId]
	if cached ~= nil then
		return cached
	end
	local ok, name = pcall(function()
		return Players:GetNameFromUserIdAsync(userId)
	end)
	local result = if ok and typeof(name) == "string" then name else "?"
	nameCache[userId] = result
	return result
end

local function topOf(week: number): { any }?
	local ok, pages = pcall(function()
		return store(week):GetSortedAsync(false, Show.Winners)
	end)
	if not ok or pages == nil then
		return nil
	end
	local rows = {}
	for rank, entry in (pages :: any):GetCurrentPage() do
		table.insert(rows, { rank = rank, userId = tonumber(entry.key), score = entry.value })
	end
	return rows
end

--- Prize check for the last closed week.
local function claim(player: Player, data: Types.ProfileData)
	local lastWeek = Show.weekIndex(os.time()) - 1
	if data.showWeekClaimed >= lastWeek then
		return
	end
	local rows = topOf(lastWeek)
	if rows == nil then
		-- The store did not answer; try again next join rather than marking the
		-- week as claimed and losing a prize to a network error.
		return
	end
	data.showWeekClaimed = lastWeek
	for _, row in rows do
		if row.userId == player.UserId then
			local season = Squishes.seasonAt(Show.weekStart(lastWeek + 1) - 1)
			local prize = Squishes.seasonalFor(season)
			if prize ~= nil then
				SquishService.give(player, data, prize.id, 1, "show")
				Remotes.toast(player, "show.won", `@squish.{prize.id}`)
			end
			if Badges.showWinner ~= 0 then
				pcall(function()
					BadgeService:AwardBadge(player.UserId, Badges.showWinner)
				end)
			end
			SquishService.refresh(player)
			return
		end
	end
end

local function board(): { any }
	local week = Show.weekIndex(os.time())
	local cache = boardCache
	if cache ~= nil and cache.week == week and os.clock() - cache.at < BOARD_CACHE_SECONDS then
		return cache.rows
	end
	local rows = topOf(week) or {}
	for _, row in rows do
		row.name = nameOf(row.userId)
	end
	boardCache = { week = week, at = os.clock(), rows = rows }
	return rows
end

function ShowService.start()
	DataService.ProfileLoaded:Connect(function(player: Player, data: Types.ProfileData)
		task.spawn(claim, player, data)
		writeScore(player, data, true)
	end)
	Players.PlayerRemoving:Connect(function(player: Player)
		local data = DataService.getData(player)
		if data ~= nil then
			writeScore(player, data, true)
		end
		lastWrite[player] = nil
	end)
	task.spawn(function()
		while true do
			task.wait(60)
			for _, player in Players:GetPlayers() do
				local data = DataService.getData(player)
				if data ~= nil then
					writeScore(player, data, false)
				end
			end
		end
	end)

	Remotes.func(Remotes.Names.GetShow).OnServerInvoke = function(player: Player)
		if not RateLimiter.consume(player, "GetShow", 3, 0.5) then
			return nil
		end
		local data = DataService.getData(player)
		if data == nil then
			return nil
		end
		local week = Show.weekIndex(os.time())
		local season = Squishes.seasonAt(os.time())
		local prize = Squishes.seasonalFor(season)
		return {
			score = Show.score(data.squishes),
			endsIn = Show.weekStart(week + 1) - os.time(),
			counted = Show.CountedSquishes,
			winners = Show.Winners,
			prize = if prize ~= nil then prize.id else nil,
			top = board(),
		}
	end
end

return ShowService
