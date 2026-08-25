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

local DataService = require(script.Parent.DataService)

local PayoutService = {}

local STORE_NAME = "PendingPayout_v1"
local FLUSH_INTERVAL_SECONDS = 30
local MAX_KEYS_PER_FLUSH = 20

local store = DataStoreService:GetDataStore(STORE_NAME)

--- Teacher user id -> points not yet written to the store.
local buffer: { [number]: number } = {}
local running = false

local function bufferAdd(userId: number, amount: number)
	local current: number = buffer[userId] or 0
	buffer[userId] = current + amount
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

local function flush()
	local keys: { number } = {}
	for userId in buffer do
		table.insert(keys, userId)
		if #keys >= MAX_KEYS_PER_FLUSH then
			break
		end
	end

	for _, userId in keys do
		local amount = buffer[userId]
		if amount == nil or amount <= 0 then
			buffer[userId] = nil
			continue
		end

		-- Clear before writing. If the write fails the amount is added back, which
		-- risks a double credit far less than holding it and writing twice.
		buffer[userId] = nil
		local ok = pcall(function()
			store:UpdateAsync(tostring(userId), function(current: any)
				local existing: number = if typeof(current) == "number" then current else 0
				return existing + amount
			end)
		end)
		if not ok then
			bufferAdd(userId, amount)
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

	local buffered = buffer[player.UserId]
	if buffered ~= nil and buffered > 0 then
		buffer[player.UserId] = nil
		data.teacher.pendingPayout += buffered
	end

	local ok, stored = pcall(function()
		return store:RemoveAsync(tostring(player.UserId))
	end)
	if ok and typeof(stored) == "number" and stored > 0 then
		local fresh = DataService.getData(player)
		if fresh ~= nil then
			fresh.teacher.pendingPayout += stored
		else
			-- The player left mid-read. Put it back rather than dropping it.
			bufferAdd(player.UserId, stored)
		end
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
	data.points += pending
	return pending
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
