--!strict
--- Settling a finished activity: statistics, the student's points, progression,
--- and what the teacher earns.
---
--- Extracted from LessonService when obstacle courses arrived. Both need exactly
--- this sequence, and two copies of a payout formula is how a game ends up
--- paying two different rates for the same work.

local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Campus = require(ReplicatedStorage.Shared.Config.Campus)
local Economy = require(ReplicatedStorage.Shared.Config.Economy)
local Progression = require(ReplicatedStorage.Shared.Config.Progression)
local Types = require(ReplicatedStorage.Shared.Types)
local Analytics = require(script.Parent.AnalyticsService)
local CampusService = require(script.Parent.CampusService)
local AchievementService = require(script.Parent.AchievementService)
local DataService = require(script.Parent.DataService)
local LessonStatsService = require(script.Parent.LessonStatsService)
local PayoutService = require(script.Parent.PayoutService)
local ProgressionService = require(script.Parent.ProgressionService)
local PurchaseService = require(script.Parent.PurchaseService)

local RewardService = {}

--- Lessons in one subject before it counts toward the polymath branch. Ten is
--- roughly a grade's worth in a single subject: enough that eight of them is a
--- real span of play, few enough that the first one lands inside a first session.
RewardService.LessonsToMasterSubject = 10

export type Settlement = {
	subject: string,
	--- What the pass rate is aggregated under: a lesson id for a teacher's work,
	--- a subject for a bank lesson.
	statKey: string,
	passed: boolean,
	--- A quiz scores answers, an obstacle course scores checkpoints. Either way
	--- this is what the student's points are computed from.
	score: number,
	total: number,
	teacherUserId: number,
	classMembers: number,
	teacherRating: number,
	translated: boolean,
	elapsedSeconds: number,
	expectedSeconds: number,
}

export type Summary = {
	passed: boolean,
	score: number,
	total: number,
	pointsAwarded: number,
	multiplier: number,
	grade: number,
	advanced: boolean,
	graduated: boolean,
}

local function creditTeacher(player: Player, data: Types.ProfileData, settlement: Settlement)
	local key = tostring(settlement.teacherUserId)
	local history = data.teacherHistory[key]
	if history == nil then
		history = { completions = 0, paid = 0 }
		data.teacherHistory[key] = history
	end

	-- Roblox account age, not how long they have played this game: a legitimate
	-- newcomer's profile is also seconds old, and a freshly registered alt is the
	-- thing being screened out.
	local counts = Economy.countsTowardTeacherPayout(player.AccountAge, data.playSeconds)

	-- Recorded either way. Otherwise a ring could park its farming on accounts
	-- that never age past the gate and reset the decay curve on every run.
	history.completions += 1
	if not counts then
		return
	end

	-- The mentor branch counts distinct students, not completions: a class of ten
	-- taken a hundred times is ten students. `completions` was just incremented,
	-- so one means this is their first, and only a student who cleared the alt
	-- gate above is counted at all.
	if history.completions == 1 then
		PayoutService.creditStat(settlement.teacherUserId, "studentsTaught", 1)
	end

	local breakdown = Economy.teacherPayout({
		priorCompletions = history.completions - 1,
		lifetimePaidByThisStudent = history.paid,
		actualSeconds = settlement.elapsedSeconds,
		expectedSeconds = settlement.expectedSeconds,
		globalPassRate = LessonStatsService.passRate(settlement.statKey),
		classMembers = settlement.classMembers,
		teacherRating = settlement.teacherRating,
		isTranslatedCompletion = settlement.translated,
	})

	if breakdown.amount <= 0 then
		return
	end
	history.paid += breakdown.amount
	PayoutService.credit(settlement.teacherUserId, breakdown.amount)
end

function RewardService.settle(player: Player, settlement: Settlement): Summary?
	LessonStatsService.record(settlement.statKey, settlement.passed)

	local data = DataService.getData(player)
	if data == nil then
		return nil
	end

	local hasDoublePass = PurchaseService.ownsPass(player, "xp2")
	local multiplier = ProgressionService.rewardMultiplier(data, hasDoublePass)
	-- The director's subject of the month and any running event fold in here.
	-- Both only ever multiply upward: nothing the office does can leave a student
	-- with less than they would have had.
	multiplier *= CampusService.bonusMultiplier(data.locale, settlement.subject)
	multiplier *= Progression.calendarMultiplier(os.time())

	local points = Economy.studentReward(settlement.score, settlement.passed, multiplier)
	data.points += points

	local outcome =
		ProgressionService.applyLesson(data, settlement.subject, settlement.passed, points)

	Analytics.lessonFinished(
		player,
		settlement.subject,
		settlement.passed,
		settlement.score,
		settlement.total
	)
	Analytics.pointsEarned(player, points, data.points, settlement.subject)
	if outcome.advanced then
		Analytics.gradeReached(player, data.grade)
	end

	-- Counters after the profile is updated, never before: a tier granted for a
	-- lesson that then failed to settle would be a reward for nothing.
	if settlement.passed then
		AchievementService.bump(player, "lessonsPassed", 1)
		if settlement.total > 0 and settlement.score >= settlement.total then
			AchievementService.bump(player, "perfectLessons", 1)
		end

		-- Mastery is recomputed rather than incremented: it is a property of the
		-- whole profile, and a counter that only ever went up by one would drift
		-- the moment the threshold moved.
		local mastered = 0
		for _, progress in data.subjects do
			if progress.lessonsPassed >= RewardService.LessonsToMasterSubject then
				mastered += 1
			end
		end
		AchievementService.record(player, "subjectsMastered", mastered)
	end

	-- Teaching yourself pays nothing, and bank content has no author to pay.
	if
		settlement.teacherUserId > 0
		and settlement.teacherUserId ~= player.UserId
	then
		creditTeacher(player, data, settlement)
	end

	-- The director takes a share of what the campus earns, minted rather than
	-- deducted -- the student keeps every point they were shown.
	local director = CampusService.get(data.locale).directorUserId
	if director > 0 and director ~= player.UserId then
		PayoutService.credit(director, points * Campus.DirectorShare)
	end

	return {
		passed = settlement.passed,
		score = settlement.score,
		total = settlement.total,
		pointsAwarded = points,
		multiplier = multiplier,
		grade = data.grade,
		advanced = outcome.advanced,
		graduated = outcome.graduated,
	}
end

return RewardService
