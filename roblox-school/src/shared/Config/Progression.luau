--!strict
--- Grade progression and the school calendar.
---
--- These are two separate clocks on purpose. Tying grade progression to the
--- in-game calendar reads well on paper and fails as a game: a school year is
--- 35 weeks, so one real day per game week puts graduation over a year away, and
--- worse, a player who plays six hours a day advances exactly as fast as one who
--- plays ten minutes. Progress is therefore driven by lessons completed, and the
--- calendar only supplies rhythm -- timetable, test weeks, holidays, events.

local Progression = {}

Progression.MaxGrade = 11

--- Lessons needed to close each grade, ramping 12 -> 22.
--- Sum over all eleven grades is 187 lessons; at roughly five minutes each that
--- is a little under sixteen hours, or three to four weeks of casual play, to
--- reach the first graduation. That is the window a first prestige wants to land in.
function Progression.lessonsForGrade(grade: number): number
	local clamped = math.clamp(grade, 1, Progression.MaxGrade)
	return 11 + clamped
end

function Progression.totalLessonsToGraduate(): number
	local total = 0
	for grade = 1, Progression.MaxGrade do
		total += Progression.lessonsForGrade(grade)
	end
	return total
end

--- One in-game week passes per real day.
Progression.RealSecondsPerGameWeek = 24 * 60 * 60
Progression.GameWeeksPerTerm = 9

function Progression.gameWeek(unixSeconds: number): number
	return math.floor(unixSeconds / Progression.RealSecondsPerGameWeek)
end

--- Test week lands on the last week of every term.
function Progression.isTestWeek(unixSeconds: number): boolean
	local week = Progression.gameWeek(unixSeconds)
	return week % Progression.GameWeeksPerTerm == Progression.GameWeeksPerTerm - 1
end

function Progression.weekInTerm(unixSeconds: number): number
	return Progression.gameWeek(unixSeconds) % Progression.GameWeeksPerTerm
end

function Progression.termIndex(unixSeconds: number): number
	return math.floor(Progression.gameWeek(unixSeconds) / Progression.GameWeeksPerTerm)
end

--- What the calendar is worth on a given day.
---
--- The calendar exists for rhythm rather than for progress -- it is why a
--- Thursday feels different from a Tuesday -- so its only mechanical effect is a
--- modest bonus during test week. Enough to be a reason to show up that day,
--- small enough that missing it is not a punishment. Like every other campus
--- bonus, it only multiplies upward.
Progression.TestWeekMultiplier = 1.2

function Progression.calendarMultiplier(unixSeconds: number): number
	return if Progression.isTestWeek(unixSeconds) then Progression.TestWeekMultiplier else 1
end

--- What a graduate may do next. Graduation is a branch, not an ending: the
--- middle option is what keeps the two-sided market fed, because it answers the
--- question every player-taught game eventually dies on -- where do the teachers
--- come from. They are the graduates, and they have just been through every
--- subject from the student side.
export type GraduationPath = "university" | "teacher" | "newGamePlus"

Progression.GraduationPaths = { "university", "teacher", "newGamePlus" } :: { GraduationPath }

--- Permanent multiplier granted per completed graduation, compounding.
Progression.NewGamePlusMultiplier = 1.35

function Progression.prestigeMultiplier(graduatedCount: number): number
	return Progression.NewGamePlusMultiplier ^ math.max(graduatedCount, 0)
end

return Progression
