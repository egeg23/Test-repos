--!strict
--- Subject experience, grade advancement and graduation.
---
--- Progress is counted in lessons rather than in calendar time. The in-game week
--- ticking over per real day gives the school its rhythm -- timetable, test
--- weeks, holidays -- but if it also drove advancement then a player who plays
--- six hours a day would progress exactly as fast as one who plays ten minutes,
--- which is the opposite of what a progression system is for.

local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Achievements = require(ReplicatedStorage.Shared.Config.Achievements)
local Limits = require(ReplicatedStorage.Shared.Config.Limits)
local Progression = require(ReplicatedStorage.Shared.Config.Progression)
local Types = require(ReplicatedStorage.Shared.Types)

local ProgressionService = {}

--- Full-rate lessons the lessonSlots pass adds to the daily allowance. Half the
--- base again: enough that a buyer notices on any day long enough to reach the
--- curve, not so much that the curve stops existing for them.
ProgressionService.LessonSlotsPassBonus = 6

export type LessonOutcome = {
	subject: string,
	passed: boolean,
	xpGained: number,
	gradeBefore: number,
	gradeAfter: number,
	advanced: boolean,
	graduated: boolean,
}

local function subjectProgress(data: Types.ProfileData, subject: string): Types.SubjectProgress
	local existing = data.subjects[subject]
	if existing ~= nil then
		return existing
	end
	local fresh: Types.SubjectProgress = { xp = 0, lessonsPassed = 0 }
	data.subjects[subject] = fresh
	return fresh
end

ProgressionService.subjectProgress = subjectProgress

--- Applies one finished lesson. Failing still grants experience: a player who
--- worked through six questions and got three wrong has learned more than one who
--- skipped the lesson, and zeroing them out teaches only that trying is
--- expensive. Advancement, however, needs a pass.
function ProgressionService.applyLesson(
	data: Types.ProfileData,
	subject: string,
	passed: boolean,
	xpGained: number
): LessonOutcome
	local progress = subjectProgress(data, subject)
	progress.xp += math.max(xpGained, 0)

	-- The day's count, rolled over on the first lesson of a new day rather than
	-- on a timer: a timer would have to fire for offline players too, and a
	-- profile that has not been touched since yesterday has nothing to roll.
	local today = math.floor(os.time() / 86400)
	if data.lessonDayStamp ~= today then
		data.lessonDayStamp = today
		data.lessonsToday = 0
	end
	data.lessonsToday += 1

	local gradeBefore = data.grade
	local advanced = false
	local graduated = false

	if passed then
		progress.lessonsPassed += 1
		data.lessonsThisGrade += 1

		local required = Progression.lessonsForGrade(data.grade)
		if data.lessonsThisGrade >= required then
			data.lessonsThisGrade = 0
			if data.grade >= Progression.MaxGrade then
				-- Held at the last grade until the player chooses a path, rather
				-- than silently rolling over and losing the moment.
				data.awaitingGraduation = true
				graduated = true
			else
				data.grade += 1
				advanced = true
			end
		end
	end

	return {
		subject = subject,
		passed = passed,
		xpGained = xpGained,
		gradeBefore = gradeBefore,
		gradeAfter = data.grade,
		advanced = advanced,
		graduated = graduated,
	}
end

function ProgressionService.isValidPath(path: string): boolean
	for _, candidate in Progression.GraduationPaths do
		if candidate == path then
			return true
		end
	end
	return false
end

--- Resolves a pending graduation. Returns false when the player has not actually
--- finished, which is also what an exploiting client sending this early hits.
function ProgressionService.graduate(data: Types.ProfileData, path: string): boolean
	if not data.awaitingGraduation or not ProgressionService.isValidPath(path) then
		return false
	end

	data.awaitingGraduation = false
	data.graduatedCount += 1
	data.lessonsThisGrade = 0

	if path == "teacher" then
		-- The answer to where teachers come from. A graduate has just been through
		-- every subject from the student side, which is the only training the role
		-- actually needs.
		data.teacher.licensed = true
		data.role = "teacher"
		data.grade = Progression.MaxGrade
	elseif path == "newGamePlus" then
		data.grade = 1
		data.subjects = {}
	else
		-- University: the next tier keeps the final grade and carries progress in.
		data.grade = Progression.MaxGrade
	end

	return true
end

--- Everything that scales a student's take-home, in one place so the ad catch-up
--- figure stays checkable.
--- Full-rate lessons this profile has beyond the base allowance: the pass, plus
--- whatever the polymath and perfectionist branches have added.
function ProgressionService.extraLessonSlots(data: Types.ProfileData): number
	local slots = Achievements.perkTotal(data.achievements, "lessonSlots")
	if data.ownedPasses.lessonSlots then
		slots += ProgressionService.LessonSlotsPassBonus
	end
	return slots
end

function ProgressionService.rewardMultiplier(
	data: Types.ProfileData,
	hasDoublePass: boolean
): number
	local multiplier = Progression.prestigeMultiplier(data.graduatedCount)
	if hasDoublePass then
		multiplier *= 2
	end
	local now = os.time()
	local doubleUntil: number = data.activeBoosts.lessonX2 or 0
	if doubleUntil > now then
		multiplier *= 2
	end
	local tripleUntil: number = data.activeBoosts.lessonX3 or 0
	if tripleUntil > now then
		multiplier *= 3
	end
	-- Earned perks multiply alongside the bought ones rather than instead of
	-- them. That is the whole shape of the three lanes: a veteran who never paid
	-- beats a newcomer who did, and a veteran who also pays beats both. The
	-- perk ceiling is held under the pass multiplier in Config/Achievements,
	-- which is what stops the free lane from turning the pass into a refund.
	multiplier *= Achievements.perkTotal(data.achievements, "studentPoints")

	-- And the day's diminishing return, last, so it scales everything else. This
	-- is the only downward factor in the function, and it is a curve rather than
	-- a cutoff on purpose: the thirty-first lesson of the day still pays, which
	-- is what keeps it a rate rather than a wall.
	multiplier *= Limits.dailyRate(data.lessonsToday, ProgressionService.extraLessonSlots(data))
	return multiplier
end

return ProgressionService
