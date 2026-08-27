--!strict
--- The limits the shop sells relief from.
---
--- This file exists because of the worst bug found in the project so far: six of
--- nine game passes, four of four consumables and four of seven ad rewards were
--- being sold and granted, and did nothing at all. "More lessons per day" lifted
--- a daily limit that had never been written. "Restore attempt" restored an
--- attempt in a game with no attempts. The grant code ran, the counter went up,
--- and no line anywhere ever read it.
---
--- So the limits are defined here first, and the things that sell relief from
--- them are wired to these numbers rather than to an intention.
---
--- One rule shapes all of them: **nothing here blocks progress.** Every limit is
--- a rate, never a wall. That is partly design -- a wall is where a session ends
--- and a player does not come back -- and partly platform policy, because an ad
--- that lifts a wall is a progression gate and Roblox does not allow one.
--- A player who has done thirty lessons today still earns from the thirty-first.
--- They just earn less than they did on the fifth.
---
--- Engine-free, like every config here, so the tests execute these functions
--- rather than a description of them.

local Limits = {}

-- === Daily lesson rate ========================================================

--- Lessons a day that pay in full. Roughly ninety minutes of play: long enough
--- that no ordinary session touches it, short enough that a marathon does.
Limits.BaseDailyFullRateLessons = 12

--- Each lesson past the limit pays this share of the one before it.
Limits.DailyDecayPerLesson = 0.88

--- And never less than this. A floor rather than zero, because zero is a wall
--- wearing a curve's clothes: the player stops, and the rule that nothing here
--- blocks progress stops being true.
Limits.MinDailyRate = 0.25

--- What the Nth lesson of the day is worth.
---
--- `extraSlots` comes from the lessonSlots pass and the perks that add to it,
--- which is what those are *for* -- they move where the curve starts bending,
--- not how steep it is. Buying a bigger allowance should feel like more of the
--- good part of the day, not like a different game.
function Limits.dailyRate(lessonsToday: number, extraSlots: number): number
	local allowance = Limits.BaseDailyFullRateLessons + math.max(extraSlots, 0)
	local over = math.max(0, lessonsToday - allowance)
	if over <= 0 then
		return 1
	end
	return math.max(Limits.MinDailyRate, Limits.DailyDecayPerLesson ^ over)
end

--- Lessons of full rate the "second wind" ad hands back.
---
--- It subtracts from the count rather than adding to the allowance so it cannot
--- stack into a permanently higher ceiling: a player who watches it twice gets
--- eight lessons back, not an allowance of twenty-eight forever.
Limits.SecondWindLessons = 4

-- === Retry cooldown ===========================================================

--- How long a failed lesson stays closed to the student who failed it.
---
--- Per lesson, not per player: failing maths does not stop you doing history.
--- The point is to make a failure cost something without ending the session, and
--- to stop a student brute-forcing one lesson's question pool by retrying it
--- twenty times in a row -- which is also the cheapest way to farm a teacher.
Limits.RetryCooldownSeconds = 300

--- A cooldown longer than this is not a cooldown, it is a lockout. Guards the
--- constant above against a well-meaning tuning pass.
Limits.MaxRetryCooldownSeconds = 1800

function Limits.retryRemaining(failedAt: number, now: number): number
	if failedAt <= 0 then
		return 0
	end
	return math.max(0, failedAt + Limits.RetryCooldownSeconds - now)
end

-- === Hints ====================================================================

--- Wrong options a hint removes, and how many hints a lesson allows.
---
--- One option, not two: removing two of four leaves a coin flip, and a lesson
--- that can be coin-flipped is not measuring understanding. Two hints per lesson
--- means the pass helps on the questions a student is stuck on without carrying
--- them through a whole test they have not learned.
Limits.HintRemovesOptions = 1
Limits.HintsPerLesson = 2

-- === Offline notes ============================================================

--- Points a minute accrued while away, for a student with the notes pass.
---
--- Small on purpose. Offline income exists to give a returning player something
--- waiting for them, not to make not playing the better strategy. The cap is
--- what enforces that: eight hours, so a night away is fully collected and a
--- fortnight away is worth the same as a night.
Limits.OfflineNotesPerMinute = 0.9
Limits.OfflineNotesCapMinutes = 480

function Limits.offlineNotes(awaySeconds: number, doubled: boolean): number
	local minutes = math.min(awaySeconds / 60, Limits.OfflineNotesCapMinutes)
	if minutes <= 0 then
		return 0
	end
	local points = minutes * Limits.OfflineNotesPerMinute
	return math.floor(points * (if doubled then 2 else 1))
end

--- Below this there is nothing worth telling the player about, and a "welcome
--- back, here are 0 points" message is worse than silence.
Limits.MinOfflineNotesToReport = 5

-- === Teacher slots ============================================================

--- Lessons one class may hold, and what a bought slot adds. Mirrors the
--- constant in ClassService, which is checked by tools/check_limits.py rather
--- than required across the client/server boundary.
Limits.BaseLessonsPerClass = 8
Limits.SlotsPerTestSlotCharge = 1

-- === Sanity ===================================================================

assert(
	Limits.RetryCooldownSeconds <= Limits.MaxRetryCooldownSeconds,
	`retry cooldown of {Limits.RetryCooldownSeconds}s is a lockout, not a cooldown`
)
assert(
	Limits.MinDailyRate > 0,
	"the daily rate floor must be above zero, or the curve is a wall"
)
assert(
	Limits.dailyRate(1, 0) == 1 and Limits.dailyRate(Limits.BaseDailyFullRateLessons, 0) == 1,
	"the allowance must pay in full up to and including its last lesson"
)
assert(
	Limits.HintRemovesOptions * Limits.HintsPerLesson < 4,
	"hints must not be able to empty a question"
)

return Limits
