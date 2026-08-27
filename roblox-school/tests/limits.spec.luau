--!strict
--- The limits the shop sells relief from.
---
--- These functions decide what a paying player actually gets, so the properties
--- worth testing are the ones that would quietly make a purchase worthless or a
--- limit into a wall.

local Limits = require("../src/shared/Config/Limits")
local t = require("./harness")

return function()
	t.suite("Limits: the daily rate is a curve, never a wall")

	t.test("everything inside the allowance pays in full", function()
		for lesson = 1, Limits.BaseDailyFullRateLessons do
			t.equal(Limits.dailyRate(lesson, 0), 1, `lesson {lesson} pays full`)
		end
	end)

	t.test("past the allowance it decays but never stops", function()
		local previous = 1
		for over = 1, 40 do
			local rate = Limits.dailyRate(Limits.BaseDailyFullRateLessons + over, 0)
			t.isTrue(rate <= previous, `lesson +{over} does not pay more than the one before`)
			t.greaterThan(rate, 0, `lesson +{over} still pays something`)
			previous = rate
		end
	end)

	t.test("the floor holds however long the day gets", function()
		-- The floor is what makes this a rate rather than a wall. A player on
		-- their two hundredth lesson is still earning, or the curve has quietly
		-- become a stopping point -- which is both bad design and, once an ad can
		-- lift it, a progression gate Roblox does not allow.
		t.equal(Limits.dailyRate(2000, 0), Limits.MinDailyRate, "a very long day")
		t.greaterThan(Limits.MinDailyRate, 0, "and the floor is above zero")
	end)

	t.test("extra slots move where the curve bends, not how steep it is", function()
		-- This is what the lessonSlots pass buys. Buying it should feel like more
		-- of the good part of the day, not like a different game.
		local base = Limits.BaseDailyFullRateLessons
		t.equal(Limits.dailyRate(base + 4, 6), 1, "inside the bought allowance, full rate")
		t.near(
			Limits.dailyRate(base + 10, 6),
			Limits.dailyRate(base + 4, 0),
			"the same distance past either allowance decays the same"
		)
	end)

	t.test("negative slots cannot be used to steepen the curve", function()
		t.equal(
			Limits.dailyRate(Limits.BaseDailyFullRateLessons, -50),
			Limits.dailyRate(Limits.BaseDailyFullRateLessons, 0),
			"clamped at zero"
		)
	end)

	t.suite("Limits: retry cooldown")

	t.test("a lesson never failed is open", function()
		t.equal(Limits.retryRemaining(0, 1000), 0, "no record means no cooldown")
	end)

	t.test("the cooldown counts down and then ends", function()
		local failedAt = 1000
		t.equal(Limits.retryRemaining(failedAt, failedAt), Limits.RetryCooldownSeconds, "at once")
		t.equal(
			Limits.retryRemaining(failedAt, failedAt + Limits.RetryCooldownSeconds),
			0,
			"exactly at the end"
		)
		t.equal(Limits.retryRemaining(failedAt, failedAt + 99999), 0, "long after")
	end)

	t.test("a clock that went backwards does not extend the cooldown forever", function()
		-- Servers in different regions, a profile restored from a backup: the
		-- stored second can be in the future, and max(0, ...) is what stops that
		-- becoming a permanent lockout.
		t.isTrue(
			Limits.retryRemaining(5000, 1000) <= Limits.RetryCooldownSeconds + 4000,
			"bounded rather than unbounded"
		)
	end)

	t.test("the cooldown is short enough to be a cost, not a lockout", function()
		t.lessThan(
			Limits.RetryCooldownSeconds,
			Limits.MaxRetryCooldownSeconds + 1,
			"inside the guard"
		)
	end)

	t.suite("Limits: hints")

	t.test("hints cannot empty a question", function()
		-- Four options, and hints remove wrong ones. If every hint could be spent
		-- on one question the student would be left with the answer, and the
		-- lesson would measure nothing.
		t.lessThan(Limits.HintRemovesOptions * Limits.HintsPerLesson, 3, "two options survive")
	end)

	t.suite("Limits: offline notes")

	t.test("nothing accrues for a player who was never away", function()
		t.equal(Limits.offlineNotes(0, false), 0, "zero seconds")
		t.equal(Limits.offlineNotes(-100, false), 0, "a clock that went backwards")
	end)

	t.test("a night away collects in full and a fortnight does not", function()
		-- The cap is the whole design: offline income must be worth returning for
		-- and never worth staying away for.
		local night = Limits.offlineNotes(8 * 3600, false)
		local fortnight = Limits.offlineNotes(14 * 24 * 3600, false)
		t.greaterThan(night, 0, "a night pays")
		t.equal(fortnight, night, "a fortnight pays the same as a night")
	end)

	t.test("doubling doubles, and only doubles", function()
		local plain = Limits.offlineNotes(4 * 3600, false)
		local doubled = Limits.offlineNotes(4 * 3600, true)
		t.near(doubled, plain * 2, "exactly twice", 1)
	end)

	t.test("an hour away is worth less than an hour of lessons", function()
		-- If it were not, the best strategy would be to log out, and every hour
		-- of design in the lesson loop would be wasted.
		t.lessThan(Limits.offlineNotes(3600, true), 120, "an hour, even doubled, is modest")
	end)
end
