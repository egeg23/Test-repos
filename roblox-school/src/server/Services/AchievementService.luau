--!strict
--- Achievement branches: counting what a player does, and paying for it.
---
--- The profile has carried an `achievements` table since the first commit and
--- nothing ever wrote to it. This is the system that was supposed to be behind
--- it: ten branches, each a track of tiers keyed to a counter, each tier paying
--- points once and granting a permanent perk.
---
--- Two rules the whole thing rests on.
---
--- **Stats only go up.** Every counter is monotonic, and `record` takes a max
--- rather than assigning. A stat that could fall would revoke a tier the player
--- has already been told they earned, and a progression system that takes things
--- back is worse than one that never gave them.
---
--- **Granting is a set difference, not a scan with side effects.** What a stat
--- value has earned is a pure function in the config; this service subtracts what
--- the profile already holds and pays the remainder. Running it twice on the same
--- data pays nothing the second time, which matters because it runs on every
--- lesson, every course and every join.
---
--- There is deliberately nothing to do on PlayerRemoving: every grant is written
--- into the profile as it happens and ProfileStore saves it, so there is no
--- pending state that a disconnect could lose.

local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Achievements = require(ReplicatedStorage.Shared.Config.Achievements)
local Remotes = require(ReplicatedStorage.Shared.Remotes)
local Types = require(ReplicatedStorage.Shared.Types)
local Analytics = require(script.Parent.AnalyticsService)
local DataService = require(script.Parent.DataService)

local AchievementService = {}

local SECONDS_PER_DAY = 86400

--- Mirrors RewardService.LessonsToMasterSubject. Not required from there because
--- RewardService requires this module, and the two would form a cycle; the value
--- is asserted equal by tools/check_achievements.py instead.
local MASTERY_LESSONS = 10

--- A gap of more than this many days ends a streak. One day is the whole point;
--- the tolerance exists because "yesterday" is a timezone question and a player
--- who returns 25 hours later has not missed a day in any sense they would
--- recognise.
AchievementService.StreakGraceDays = 1

local function dayNumber(unixSeconds: number): number
	return math.floor(unixSeconds / SECONDS_PER_DAY)
end

--- Pays out every tier `data` has reached but not yet been granted.
---
--- Returns the tiers granted, so the caller can tell the player. Nothing is sent
--- from in here: this runs inside lesson settlement, and a service that both
--- mutates a profile and talks to a client is one that eventually does the second
--- part when the first has failed.
local function grantPending(data: Types.ProfileData): { { branch: string, tier: number, points: number } }
	local granted = {}
	for _, branch in Achievements.Branches do
		local value = data.stats[branch.stat] or 0
		for _, id in Achievements.earned(branch, value) do
			if data.achievements[id] then
				continue
			end
			local _, indexText = string.match(id, "^(.-):(%d+)$")
			local index = tonumber(indexText)
			if index == nil then
				continue
			end
			local tier = branch.tiers[index]
			if tier == nil then
				continue
			end
			data.achievements[id] = true
			data.points += tier.points
			table.insert(granted, { branch = branch.id, tier = index, points = tier.points })
		end
	end
	return granted
end

local function announce(player: Player, granted: { { branch: string, tier: number, points: number } })
	if #granted == 0 then
		return
	end
	for _, entry in granted do
		Analytics.achievementUnlocked(player, entry.branch, entry.tier)
	end
	Remotes.event(Remotes.Names.AchievementUnlocked):FireClient(player, granted)
end

--- Raises a counter to at least `value` and pays anything that unlocks.
---
--- Max rather than assign, so a caller that reports a stale or lower value -- a
--- late lesson settling after a newer one, a recount after a migration -- cannot
--- walk a counter backwards.
function AchievementService.record(player: Player, stat: string, value: number)
	local data = DataService.getData(player)
	if data == nil then
		return
	end
	local current = data.stats[stat] or 0
	if value <= current then
		return
	end
	data.stats[stat] = value
	announce(player, grantPending(data))
end

--- Adds to a counter. The common case: one more lesson, one more course.
function AchievementService.bump(player: Player, stat: string, amount: number?)
	local data = DataService.getData(player)
	if data == nil then
		return
	end
	local step = amount or 1
	if step <= 0 then
		return
	end
	data.stats[stat] = (data.stats[stat] or 0) + step
	announce(player, grantPending(data))
end

--- What this player's unlocked tiers add up to for one effect.
---
--- Returns the identity (1 for multipliers, 0 for counts) when the profile is
--- not loaded, so a caller during a load race gets an unmodified game rather
--- than an error or a zeroed multiplier.
function AchievementService.perk(player: Player, effect: Achievements.Effect): number
	local data = DataService.getData(player)
	if data == nil then
		return if Achievements.Multiplicative[effect] then 1 else 0
	end
	return Achievements.perkTotal(data.achievements, effect)
end

--- Credits today toward the daily streak, and returns the streak length.
---
--- Called on join and idempotent within a day: a player who joins four times
--- before midnight has a streak of one day, not four. A gap longer than the
--- grace resets to one rather than to zero, because the session they are in
--- right now is itself day one of the next streak.
function AchievementService.touchDaily(player: Player): number
	local data = DataService.getData(player)
	if data == nil then
		return 0
	end

	local today = dayNumber(os.time())
	if data.streakDay == today then
		return data.streak
	end

	local gap = today - data.streakDay
	if data.streakDay > 0 and gap <= AchievementService.StreakGraceDays + 1 then
		data.streak += 1
	else
		data.streak = 1
	end
	data.streakDay = today

	AchievementService.record(player, "longestStreak", data.streak)
	Analytics.dailyStreak(player, data.streak)
	Remotes.event(Remotes.Names.StreakState):FireClient(player, { days = data.streak })
	return data.streak
end

--- The whole board, for the panel: every branch, the player's counter, which
--- tiers are unlocked and what the next one costs.
function AchievementService.board(player: Player): any
	local data = DataService.getData(player)
	if data == nil then
		return nil
	end

	local branches = {}
	for _, branch in Achievements.Branches do
		-- A student is not shown the teaching branches until they are licensed.
		-- Ten branches with five permanently greyed out reads as a paywall on a
		-- first session, and it is not one.
		if branch.audience == "teacher" and not data.teacher.licensed then
			continue
		end

		local value = data.stats[branch.stat] or 0
		local tiers = {}
		for index, tier in branch.tiers do
			table.insert(tiers, {
				at = tier.at,
				points = tier.points,
				effect = tier.perk.effect,
				value = tier.perk.value,
				unlocked = data.achievements[Achievements.tierId(branch.id, index)] == true,
			})
		end
		table.insert(branches, {
			id = branch.id,
			displayKey = branch.displayKey,
			value = value,
			tiers = tiers,
		})
	end

	return {
		branches = branches,
		streak = data.streak,
		perks = {
			studentPoints = Achievements.perkTotal(data.achievements, "studentPoints"),
			teacherPayout = Achievements.perkTotal(data.achievements, "teacherPayout"),
			adReward = Achievements.perkTotal(data.achievements, "adReward"),
			obstacleTime = Achievements.perkTotal(data.achievements, "obstacleTime"),
			classCapacity = Achievements.perkTotal(data.achievements, "classCapacity"),
			lessonSlots = Achievements.perkTotal(data.achievements, "lessonSlots"),
			attemptRefund = Achievements.perkTotal(data.achievements, "attemptRefund"),
		},
	}
end

function AchievementService.start()
	-- Profiles that predate this system arrive with the counters at zero but a
	-- history behind them, so the two stats already stored elsewhere are seeded
	-- from it. The rest start where the player is now, which under-credits a
	-- returning player once and never again -- the alternative is inventing a
	-- number, and a fabricated counter is worse than a late one.
	DataService.ProfileLoaded:Connect(function(player: Player)
		local data = DataService.getData(player)
		if data == nil then
			return
		end

		AchievementService.record(player, "graduatedCount", data.graduatedCount)

		local lessons = 0
		local mastered = 0
		for _, progress in data.subjects do
			lessons += progress.lessonsPassed
			if progress.lessonsPassed >= MASTERY_LESSONS then
				mastered += 1
			end
		end
		AchievementService.record(player, "lessonsPassed", lessons)
		AchievementService.record(player, "subjectsMastered", mastered)

		AchievementService.touchDaily(player)
	end)
end

return AchievementService
