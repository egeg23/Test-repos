--!strict
--- Per-language campuses: the monthly election, the deans, and what the office
--- can actually do.
---
--- Hierarchy is per locale while the economy and the content pool stay global.
--- With one worldwide director the largest language wins every election forever
--- and every other community loses the entire political layer -- which is the
--- part of the design that brings people back on a day they have no lessons left.
---
--- The term rolls over lazily. There is no scheduled job: the first server to
--- notice the calendar has moved counts the previous cycle's votes and installs
--- the winner, conditionally, so if six servers notice at once exactly one write
--- takes effect.

local DataStoreService = game:GetService("DataStoreService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Campus = require(ReplicatedStorage.Shared.Config.Campus)
local Progression = require(ReplicatedStorage.Shared.Config.Progression)
local Subjects = require(ReplicatedStorage.Shared.Config.Subjects)
local DataService = require(script.Parent.DataService)

local CampusService = {}

local CACHE_TTL_SECONDS = 30
local MIN_DEAN_RATING = 3.0

local campusStore = DataStoreService:GetDataStore("Campus_v1")
local voteStore = DataStoreService:GetDataStore("CampusVotes_v1")

export type Record = {
	cycleIndex: number,
	directorUserId: number,
	directorName: string,
	--- Consecutive terms the sitting director has served, so the term limit can
	--- be enforced when they try to stand again.
	consecutiveTerms: number,
	subjectOfMonth: string?,
	motto: string?,
	eventsUsed: number,
	eventUntil: number,
	deans: { [string]: number },
	deanNames: { [string]: string },
}

type Candidate = { name: string, votes: number }
type Ballot = { candidate: string, weight: number }
type Votes = {
	candidates: { [string]: Candidate },
	--- Voter user id -> their ballot. The weight is stored with it, not
	--- recomputed on change: a voter who plays another day between casting and
	--- changing their vote would otherwise take more away from the first
	--- candidate than they ever gave, and enough of that drives a tally negative.
	voters: { [string]: Ballot },
}

type CacheEntry = { record: Record, fetchedAt: number }
local cache: { [string]: CacheEntry } = {}

local function emptyRecord(cycleIndex: number): Record
	return {
		cycleIndex = cycleIndex,
		directorUserId = 0,
		directorName = "",
		consecutiveTerms = 0,
		subjectOfMonth = nil,
		motto = nil,
		eventsUsed = 0,
		eventUntil = 0,
		deans = {},
		deanNames = {},
	}
end

local function emptyVotes(): Votes
	return { candidates = {}, voters = {} }
end

local function voteKey(locale: string, cycleIndex: number): string
	return `{locale}:{cycleIndex}`
end

local function readVotes(locale: string, cycleIndex: number): Votes
	local ok, value = pcall(function()
		return voteStore:GetAsync(voteKey(locale, cycleIndex))
	end)
	if ok and typeof(value) == "table" then
		return value :: Votes
	end
	return emptyVotes()
end

local function winnerOf(votes: Votes): (number, string)
	local bestId, bestName, bestVotes = 0, "", 0
	for userId, candidate in votes.candidates do
		-- Ties go to the lower user id, which is arbitrary but stable: every
		-- server that counts these votes has to reach the same answer.
		local numeric = tonumber(userId) or 0
		if
			candidate.votes > bestVotes
			or (candidate.votes == bestVotes and bestId ~= 0 and numeric < bestId)
		then
			bestId, bestName, bestVotes = numeric, candidate.name, candidate.votes
		end
	end
	return bestId, bestName
end

--- Installs the winner of the cycle that just ended, if nobody has yet.
local function rollover(locale: string, currentCycle: number): Record
	local counted = readVotes(locale, currentCycle - 1)
	local winnerId, winnerName = winnerOf(counted)

	local result: Record? = nil
	pcall(function()
		campusStore:UpdateAsync(locale, function(current: any)
			local record: Record = if typeof(current) == "table"
				then current :: Record
				else emptyRecord(currentCycle)

			if record.cycleIndex >= currentCycle then
				-- Another server got here first. Take theirs.
				result = record
				return nil
			end

			local previousDirector = record.directorUserId
			record.cycleIndex = currentCycle
			record.directorUserId = winnerId
			record.directorName = winnerName
			record.consecutiveTerms = if winnerId ~= 0 and winnerId == previousDirector
				then record.consecutiveTerms + 1
				else (if winnerId ~= 0 then 1 else 0)
			-- A new term starts with a clean slate: no subject of the month, no
			-- spent events, and deans to appoint.
			record.subjectOfMonth = nil
			record.eventsUsed = 0
			record.eventUntil = 0
			record.deans = {}
			record.deanNames = {}

			result = record
			return record
		end)
	end)

	if result ~= nil then
		return result
	end
	-- The write failed outright; serve a blank term rather than last month's.
	return emptyRecord(currentCycle)
end

function CampusService.get(locale: string, fresh: boolean?): Record
	local currentCycle = Campus.cycleIndex(os.time())
	local entry = cache[locale]
	if
		not fresh
		and entry ~= nil
		and entry.record.cycleIndex == currentCycle
		and os.clock() - entry.fetchedAt < CACHE_TTL_SECONDS
	then
		return entry.record
	end

	local ok, value = pcall(function()
		return campusStore:GetAsync(locale)
	end)
	local record: Record = if ok and typeof(value) == "table"
		then value :: Record
		else emptyRecord(currentCycle)

	if record.cycleIndex < currentCycle then
		record = rollover(locale, currentCycle)
	end

	cache[locale] = { record = record, fetchedAt = os.clock() }
	return record
end

function CampusService.isDirector(locale: string, userId: number): boolean
	return CampusService.get(locale).directorUserId == userId
end

function CampusService.isDean(locale: string, subject: string, userId: number): boolean
	return CampusService.get(locale).deans[subject] == userId
end

--- Everything the office grants, folded into one number the reward path reads.
function CampusService.bonusMultiplier(locale: string, subject: string): number
	local record = CampusService.get(locale)
	local multiplier = 1
	if record.subjectOfMonth == subject then
		multiplier *= Campus.SubjectOfMonthMultiplier
	end
	if record.eventUntil > os.time() then
		multiplier *= Campus.EventMultiplier
	end
	return multiplier
end

local function mutate(locale: string, transform: (Record) -> Record?): Record?
	local result: Record? = nil
	local ok = pcall(function()
		campusStore:UpdateAsync(locale, function(current: any)
			if typeof(current) ~= "table" then
				return nil
			end
			local updated = transform(current :: Record)
			if updated == nil then
				result = nil
				return nil
			end
			result = updated
			return updated
		end)
	end)
	if ok and result ~= nil then
		cache[locale] = { record = result, fetchedAt = os.clock() }
	end
	return result
end

function CampusService.nominate(player: Player): (boolean, string?)
	local data = DataService.getData(player)
	if data == nil then
		return false, "notLoaded"
	end
	if Campus.phase(os.time()) ~= "campaign" then
		return false, "notCampaign"
	end
	if not data.teacher.licensed then
		return false, "notLicensed"
	end
	if data.teacher.ratingCount < Campus.MinRatingCountToStand then
		return false, "notEnoughRatings"
	end
	if data.teacher.rating < Campus.MinRatingToStand then
		return false, "ratingTooLow"
	end

	local record = CampusService.get(data.locale)
	if
		record.directorUserId == player.UserId
		and record.consecutiveTerms >= Campus.MaxConsecutiveTerms
	then
		return false, "termLimit"
	end

	local cycle = Campus.cycleIndex(os.time())
	local ok = pcall(function()
		voteStore:UpdateAsync(voteKey(data.locale, cycle), function(current: any)
			local votes: Votes = if typeof(current) == "table"
				then current :: Votes
				else emptyVotes()
			local key = tostring(player.UserId)
			if votes.candidates[key] == nil then
				votes.candidates[key] = { name = player.DisplayName, votes = 0 }
			end
			return votes
		end)
	end)
	return ok, if ok then nil else "storeFailed"
end

function CampusService.vote(player: Player, candidateUserId: unknown): (boolean, string?)
	if typeof(candidateUserId) ~= "number" then
		return false, "badRequest"
	end
	local data = DataService.getData(player)
	if data == nil then
		return false, "notLoaded"
	end
	if Campus.phase(os.time()) ~= "voting" then
		return false, "notVoting"
	end
	if not Campus.canVote(player.AccountAge, data.playSeconds) then
		return false, "notEligible"
	end

	local weight = Campus.voteWeight(data.playSeconds)
	local cycle = Campus.cycleIndex(os.time())
	local target = tostring(math.floor(candidateUserId :: number))
	local applied = false

	local ok = pcall(function()
		voteStore:UpdateAsync(voteKey(data.locale, cycle), function(current: any)
			if typeof(current) ~= "table" then
				return nil
			end
			local votes = current :: Votes
			if votes.candidates[target] == nil then
				return nil
			end

			-- Changing your mind moves the ballot rather than adding another one,
			-- and moves exactly the weight it was cast with.
			local voterKey = tostring(player.UserId)
			local previous = votes.voters[voterKey]
			if previous ~= nil then
				local prior = votes.candidates[previous.candidate]
				if prior ~= nil then
					prior.votes = math.max(0, prior.votes - previous.weight)
				end
			end
			votes.candidates[target].votes += weight
			votes.voters[voterKey] = { candidate = target, weight = weight }
			applied = true
			return votes
		end)
	end)

	if not ok then
		return false, "storeFailed"
	end
	return applied, if applied then nil else "noCandidate"
end

function CampusService.standings(locale: string, userId: number?): any
	local now = os.time()
	local cycle = Campus.cycleIndex(now)
	local votes = readVotes(locale, cycle)
	local record = CampusService.get(locale)

	local candidates: { any } = {}
	for userId, candidate in votes.candidates do
		table.insert(candidates, {
			userId = tonumber(userId) or 0,
			name = candidate.name,
			votes = candidate.votes,
		})
	end
	table.sort(candidates, function(a, b)
		return a.votes > b.votes
	end)

	-- Which offices this player holds, so the interface can offer the controls
	-- that go with them instead of guessing from a name.
	local deanOf: { string } = {}
	if userId ~= nil then
		for subject, holder in record.deans do
			if holder == userId then
				table.insert(deanOf, subject)
			end
		end
	end

	return {
		deanOf = deanOf,
		phase = Campus.phase(now),
		dayInCycle = Campus.dayInCycle(now),
		cycleDays = Campus.CycleDays,
		schoolWeek = Progression.gameWeek(now),
		weekInTerm = Progression.weekInTerm(now),
		weeksPerTerm = Progression.GameWeeksPerTerm,
		termIndex = Progression.termIndex(now),
		isTestWeek = Progression.isTestWeek(now),
		directorUserId = record.directorUserId,
		directorName = record.directorName,
		subjectOfMonth = record.subjectOfMonth,
		motto = record.motto,
		eventUntil = record.eventUntil,
		eventsLeft = math.max(0, Campus.EventsPerTerm - record.eventsUsed),
		deans = record.deanNames,
		candidates = candidates,
	}
end

function CampusService.setSubjectOfMonth(player: Player, subject: unknown): (boolean, string?)
	local data = DataService.getData(player)
	if data == nil then
		return false, "notLoaded"
	end
	if typeof(subject) ~= "string" or Subjects.get(subject :: string) == nil then
		return false, "unknownSubject"
	end
	if not CampusService.isDirector(data.locale, player.UserId) then
		return false, "notDirector"
	end

	local updated = mutate(data.locale, function(record)
		record.subjectOfMonth = subject :: string
		return record
	end)
	return updated ~= nil, if updated ~= nil then nil else "storeFailed"
end

function CampusService.setMotto(player: Player, motto: unknown): (boolean, string?)
	local data = DataService.getData(player)
	if data == nil then
		return false, "notLoaded"
	end
	-- From a fixed list, never typed. A motto every player in the campus reads is
	-- exactly the free-form creation the experience must not offer.
	if typeof(motto) ~= "string" or not Campus.isMotto(motto :: string) then
		return false, "unknownMotto"
	end
	if not CampusService.isDirector(data.locale, player.UserId) then
		return false, "notDirector"
	end

	local updated = mutate(data.locale, function(record)
		record.motto = motto :: string
		return record
	end)
	return updated ~= nil, if updated ~= nil then nil else "storeFailed"
end

function CampusService.startEvent(player: Player): (boolean, string?)
	local data = DataService.getData(player)
	if data == nil then
		return false, "notLoaded"
	end
	if not CampusService.isDirector(data.locale, player.UserId) then
		return false, "notDirector"
	end

	local updated = mutate(data.locale, function(record)
		if record.eventsUsed >= Campus.EventsPerTerm then
			return nil
		end
		if record.eventUntil > os.time() then
			return nil
		end
		record.eventsUsed += 1
		record.eventUntil = os.time() + Campus.EventDurationSeconds
		return record
	end)
	return updated ~= nil, if updated ~= nil then nil else "noEventsLeft"
end

--- Deans are appointed rather than elected, and only from teachers who are
--- present: their rating has to be read off a live profile, and an office handed
--- to someone who never logs in moderates nothing.
function CampusService.appointDean(
	player: Player,
	subject: unknown,
	teacherUserId: unknown
): (boolean, string?)
	local data = DataService.getData(player)
	if data == nil then
		return false, "notLoaded"
	end
	if typeof(subject) ~= "string" or Subjects.get(subject :: string) == nil then
		return false, "unknownSubject"
	end
	if typeof(teacherUserId) ~= "number" then
		return false, "badRequest"
	end
	if not CampusService.isDirector(data.locale, player.UserId) then
		return false, "notDirector"
	end

	local target = Players:GetPlayerByUserId(math.floor(teacherUserId :: number))
	if target == nil then
		return false, "teacherOffline"
	end
	local targetData = DataService.getData(target)
	if targetData == nil or not targetData.teacher.licensed then
		return false, "notATeacher"
	end
	if targetData.locale ~= data.locale then
		return false, "wrongCampus"
	end
	if targetData.teacher.rating < MIN_DEAN_RATING then
		return false, "ratingTooLow"
	end

	local updated = mutate(data.locale, function(record)
		record.deans[subject :: string] = target.UserId
		record.deanNames[subject :: string] = target.DisplayName
		return record
	end)
	return updated ~= nil, if updated ~= nil then nil else "storeFailed"
end

return CampusService
