--!strict
--- Settling a finished activity: statistics, the student's points, progression,
--- and what the teacher earns.
---
--- Extracted from LessonService when obstacle courses arrived. Both need exactly
--- this sequence, and two copies of a payout formula is how a game ends up
--- paying two different rates for the same work.

local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Economy = require(ReplicatedStorage.Shared.Config.Economy)
local Types = require(ReplicatedStorage.Shared.Types)
local DataService = require(script.Parent.DataService)
local LessonStatsService = require(script.Parent.LessonStatsService)
local PayoutService = require(script.Parent.PayoutService)
local ProgressionService = require(script.Parent.ProgressionService)
local PurchaseService = require(script.Parent.PurchaseService)

local RewardService = {}

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
	local points = Economy.studentReward(settlement.score, settlement.passed, multiplier)
	data.points += points

	local outcome =
		ProgressionService.applyLesson(data, settlement.subject, settlement.passed, points)

	-- Teaching yourself pays nothing, and bank content has no author to pay.
	if
		settlement.teacherUserId > 0
		and settlement.teacherUserId ~= player.UserId
	then
		creditTeacher(player, data, settlement)
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
