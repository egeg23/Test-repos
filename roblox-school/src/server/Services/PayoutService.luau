--!strict
--- Credits teachers for lessons taken while they were not around.
---
--- Lessons are asynchronous by design, so the common case is that the teacher is
--- offline when their work earns something. Credit therefore goes straight into
--- the profile when they happen to be online, and into a DataStore queue when
--- they are not, drained the next time they log in.
---
--- Writes are buffered rather than issued per completion: a popular teacher can
--- be credited many times a minute, and DataStore write budget is per key per
--- minute. The trade-off is that a server crash loses at most one flush interval
--- of credit, which is the right side to err on -- the alternative is throttled
--- writes that lose far more.

local DataStoreService = game:GetService("DataStoreService")
local Players = game:GetService("Players")

local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Achievements = require(ReplicatedStorage.Shared.Config.Achievements)
local AchievementService = require(script.Parent.AchievementService)
local DataService = require(script.Parent.DataService)

local PayoutService = {}

local STORE_NAME = "PendingPayout_v1"
local FLUSH_INTERVAL_SECONDS = 30
local MAX_KEYS_PER_FLUSH = 20

local store = DataStoreService:GetDataStore(STORE_NAME)

--- What is owed to a teacher who is not here: points, and the achievement
--- counters their lesson moved. Both have the same delivery problem -- the
--- teacher is usually offline when their work earns anything -- so they take the
--- same queue rather than a second one that could drift out of step with it.
export type Owed = { points: number, stats: { [string]: number } }

local buffer: { [number]: Owed } = {}
local running = false

local function owed(userId: number): Owed
	local current = buffer[userId]
	if current == nil then
		current = { points = 0, stats = {} }
		buffer[userId] = current
	end
	return current
end

local function bufferAdd(userId: number, amount: number)
	owed(userId).points += amount
end

local function bufferStat(userId: number, stat: string, amount: number)
	local entry = owed(userId)
	entry.stats[stat] = (entry.stats[stat] or 0) + amount
end

--- Records read back from the store may be a bare number: that is the shape this
--- queue had before it carried counters, and a teacher who was owed points when
--- the game updated still has one sitting in the store.
local function asOwed(value: any): Owed
	if typeof(value) == "number" then
		return { points = value, stats = {} }
	end
	if typeof(value) == "table" then
		return {
			points = if typeof(value.points) == "number" then value.points else 0,
			stats = if typeof(value.stats) == "table" then value.stats else {},
		}
	end
	return { points = 0, stats = {} }
end

--- Applies `amount` to a teacher, wherever they are.
function PayoutService.credit(teacherUserId: number, amount: number)
	if amount <= 0 or teacherUserId <= 0 then
		return
	end

	local player = Players:GetPlayerByUserId(teacherUserId)
	if player ~= nil then
		local data = DataService.getData(player)
		if data ~= nil then
			data.teacher.pendingPayout += amount
			return
		end
	end

	bufferAdd(teacherUserId, amount)
end

--- Raises one of a teacher's achievement counters, wherever they are.
---
--- Needed because the counters that describe teaching -- students taught, five
--- star ratings -- are moved by something a *student* did, at a moment when the
--- teacher is usually not in the server to be told about it.
function PayoutService.creditStat(teacherUserId: number, stat: string, amount: number)
	if amount <= 0 or teacherUserId <= 0 then
		return
	end

	local player = Players:GetPlayerByUserId(teacherUserId)
	if player ~= nil and DataService.getData(player) ~= nil then
		AchievementService.bump(player, stat, amount)
		return
	end

	bufferStat(teacherUserId, stat, amount)
end

local function flush()
	local keys: { number } = {}
	for userId in buffer do
		table.insert(keys, userId)
		if #keys >= MAX_KEYS_PER_FLUSH then
			break
		end
	end

	for _, userId in keys do
		local entry = buffer[userId]
		if entry == nil or (entry.points <= 0 and next(entry.stats) == nil) then
			buffer[userId] = nil
			continue
		end

		-- Clear before writing. If the write fails the amount is added back, which
		-- risks a double credit far less than holding it and writing twice.
		buffer[userId] = nil
		local ok = pcall(function()
			store:UpdateAsync(tostring(userId), function(current: any)
				local existing = asOwed(current)
				existing.points += entry.points
				for stat, amount in entry.stats do
					existing.stats[stat] = (existing.stats[stat] or 0) + amount
				end
				return existing
			end)
		end)
		if not ok then
			bufferAdd(userId, entry.points)
			for stat, amount in entry.stats do
				bufferStat(userId, stat, amount)
			end
		end
	end
end

--- Moves anything owed into the profile. Checks the in-memory buffer as well as
--- the store: a teacher who logs in between a credit and the next flush would
--- otherwise not see it until the flush after their next login.
function PayoutService.drain(player: Player)
	local data = DataService.getData(player)
	if data == nil then
		return
	end

	local function apply(entry: Owed)
		local fresh = DataService.getData(player)
		if fresh == nil then
			-- The player left mid-read. Put it back rather than dropping it.
			bufferAdd(player.UserId, entry.points)
			for stat, amount in entry.stats do
				bufferStat(player.UserId, stat, amount)
			end
			return
		end
		fresh.teacher.pendingPayout += entry.points
		for stat, amount in entry.stats do
			AchievementService.bump(player, stat, amount)
		end
	end

	local buffered = buffer[player.UserId]
	if buffered ~= nil then
		buffer[player.UserId] = nil
		apply(buffered)
	end

	local ok, stored = pcall(function()
		return store:RemoveAsync(tostring(player.UserId))
	end)
	if ok and stored ~= nil then
		apply(asOwed(stored))
	end
end

--- Turns accrued teaching income into spendable points.
function PayoutService.collect(player: Player): number
	local data = DataService.getData(player)
	if data == nil then
		return 0
	end
	local pending = math.floor(data.teacher.pendingPayout)
	if pending <= 0 then
		return 0
	end
	data.teacher.pendingPayout -= pending

	-- The teaching perk is applied here rather than at credit time, because
	-- credit usually happens while the teacher is offline and their profile --
	-- and therefore their perks -- cannot be read. Collection is the one moment
	-- they are certainly present. The side effect is that income earned before a
	-- perk unlocked is paid at the new rate if it was left uncollected, which is
	-- a small generosity in the player's favour and not worth a second ledger.
	local paid = math.floor(pending * Achievements.perkTotal(data.achievements, "teacherPayout"))
	data.points += paid
	return paid
end

function PayoutService.start()
	if running then
		return
	end
	running = true

	DataService.ProfileLoaded:Connect(function(player: Player)
		task.spawn(PayoutService.drain, player)
	end)

	task.spawn(function()
		while running do
			task.wait(FLUSH_INTERVAL_SECONDS)
			pcall(flush)
		end
	end)

	game:BindToClose(function()
		running = false
		pcall(flush)
	end)
end

return PayoutService
