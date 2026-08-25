--!strict
--- Cross-server pass-rate statistics, which feed the quality factor.
---
--- These have to be global. A lesson judged on one quiet server's handful of
--- attempts would swing wildly, and the quality factor is what decides whether a
--- teacher is paid -- so the noise would land directly on someone's income.
---
--- Reads never yield. `passRate` answers from a local cache and, on a miss,
--- returns the neutral value and kicks off a fetch in the background. A lesson
--- finishing is not the moment to block on a network round trip, and being
--- neutral for one attempt costs nothing.

local MemoryStoreService = game:GetService("MemoryStoreService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Economy = require(ReplicatedStorage.Shared.Config.Economy)

local LessonStatsService = {}

--- Below this, a pass rate is noise. A new teacher's first lesson should not be
--- priced on three attempts.
local MIN_SAMPLES = 20
local ENTRY_TTL_SECONDS = 7 * 24 * 60 * 60
local FLUSH_INTERVAL_SECONDS = 20
local CACHE_TTL_SECONDS = 60
local MAX_KEYS_PER_FLUSH = 25

local map = MemoryStoreService:GetHashMap("LessonStats_v1")

type Counts = { attempts: number, passes: number }

local pending: { [string]: Counts } = {}
local cache: { [string]: Counts } = {}
local cachedAt: { [string]: number } = {}
local fetching: { [string]: boolean } = {}
local running = false

local NEUTRAL = (Economy.QualityBandLow + Economy.QualityBandHigh) / 2

local function readCounts(value: any): Counts
	if typeof(value) == "table" then
		local attempts = (value :: any).attempts
		local passes = (value :: any).passes
		if typeof(attempts) == "number" and typeof(passes) == "number" then
			return { attempts = attempts, passes = passes }
		end
	end
	return { attempts = 0, passes = 0 }
end

local function fetch(key: string)
	if fetching[key] then
		return
	end
	fetching[key] = true
	task.spawn(function()
		local ok, value = pcall(function()
			return map:GetAsync(key)
		end)
		if ok then
			cache[key] = readCounts(value)
			cachedAt[key] = os.clock()
		end
		fetching[key] = nil
	end)
end

--- Records one finished attempt. Buffered; the write happens on the next flush.
function LessonStatsService.record(key: string, passed: boolean)
	local entry = pending[key]
	if entry == nil then
		entry = { attempts = 0, passes = 0 }
		pending[key] = entry
	end
	entry.attempts += 1
	if passed then
		entry.passes += 1
	end
end

--- Never yields. Returns the neutral band centre when there is not enough
--- evidence yet, which is also what an unknown key gets.
function LessonStatsService.passRate(key: string): number
	local cached = cache[key]
	local age = cachedAt[key]
	if cached == nil or age == nil or os.clock() - age > CACHE_TTL_SECONDS then
		fetch(key)
		if cached == nil then
			return NEUTRAL
		end
	end

	local attempts = cached.attempts
	local passes = cached.passes
	-- Fold in what this server has seen but not yet written, so a busy server
	-- reacts to a suddenly trivial test without waiting for a flush.
	local local_ = pending[key]
	if local_ ~= nil then
		attempts += local_.attempts
		passes += local_.passes
	end

	if attempts < MIN_SAMPLES then
		return NEUTRAL
	end
	return passes / attempts
end

local function flush()
	local keys: { string } = {}
	for key in pending do
		table.insert(keys, key)
		if #keys >= MAX_KEYS_PER_FLUSH then
			break
		end
	end

	for _, key in keys do
		local delta = pending[key]
		if delta == nil then
			continue
		end
		pending[key] = nil

		local ok, updated = pcall(function()
			return map:UpdateAsync(key, function(current: any)
				local counts = readCounts(current)
				counts.attempts += delta.attempts
				counts.passes += delta.passes
				return counts
			end, ENTRY_TTL_SECONDS)
		end)

		if ok then
			cache[key] = readCounts(updated)
			cachedAt[key] = os.clock()
		else
			-- Put the delta back rather than losing the sample.
			local restored = pending[key]
			if restored == nil then
				pending[key] = delta
			else
				restored.attempts += delta.attempts
				restored.passes += delta.passes
			end
		end
	end
end

function LessonStatsService.start()
	if running then
		return
	end
	running = true

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

return LessonStatsService
