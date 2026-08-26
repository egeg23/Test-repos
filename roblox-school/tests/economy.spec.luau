--!strict
--- Runs the real Economy functions, not a description of them.

local Economy = require("../src/shared/Config/Economy")
local t = require("./harness")

return function()
	t.suite("Economy: uniqueness decay")

	t.test("a student's first completion is worth full value", function()
		t.equal(Economy.uniquenessFactor(0), 1, "first completion")
	end)

	t.test("repeats decay geometrically", function()
		t.near(Economy.uniquenessFactor(1), Economy.UniquenessDecay, "second completion")
		t.near(Economy.uniquenessFactor(2), Economy.UniquenessDecay ^ 2, "third completion")
	end)

	t.test("decay stops at the floor rather than reaching zero", function()
		t.equal(Economy.uniquenessFactor(999), Economy.UniquenessFloor, "hundredth completion")
	end)

	t.suite("Economy: engagement")

	t.test("a completion far faster than possible is worth nothing", function()
		t.equal(Economy.engagementFactor(1, 150), 0, "one second on a 150 second lesson")
	end)

	t.test("time spent is clamped at both ends", function()
		t.equal(Economy.engagementFactor(1, 100), 0, "well below the floor is invalid")
		t.equal(Economy.engagementFactor(30, 100), Economy.EngagementMin, "quick but plausible")
		t.equal(Economy.engagementFactor(10000, 100), Economy.EngagementMax, "idling all day")
	end)

	t.suite("Economy: test quality")

	t.test("a pass rate inside the band is not penalised", function()
		t.equal(Economy.qualityFactor(Economy.QualityBandLow), 1, "bottom of the band")
		t.equal(Economy.qualityFactor(0.65), 1, "middle of the band")
		t.equal(Economy.qualityFactor(Economy.QualityBandHigh), 1, "top of the band")
	end)

	t.test("a test everyone passes collapses in value", function()
		t.lessThan(Economy.qualityFactor(0.99), 0.25, "99% pass rate")
	end)

	t.test("too easy is punished harder than too hard", function()
		-- Trivial tests are the farming route; hard ones are merely bad teaching.
		t.lessThan(
			Economy.qualityFactor(1),
			Economy.qualityFactor(0),
			"impossible beats trivial"
		)
	end)

	t.suite("Economy: class fill")

	t.test("a fuller class pays more per student", function()
		local previous = -1
		for members = 0, Economy.BaseClassCapacity do
			local factor = Economy.fillRateFactor(members)
			t.greaterThan(factor, previous, `fill at {members} members`)
			previous = factor
		end
	end)

	t.test("buying capacity never lowers the rate", function()
		-- The trap this guards: measuring fill against purchased capacity meant
		-- buying seats you had not filled yet cut your income.
		local full = Economy.fillRateFactor(Economy.BaseClassCapacity)
		local expanded = Economy.fillRateFactor(Economy.BaseClassCapacity + Economy.CapacityPassBonus)
		t.equal(expanded, full, "rate after buying extra seats")
	end)

	t.suite("Economy: teacher payout")

	local function input(overrides: { [string]: any }): any
		local base = {
			priorCompletions = 0,
			lifetimePaidByThisStudent = 0,
			actualSeconds = 150,
			expectedSeconds = 150,
			globalPassRate = 0.65,
			classMembers = 20,
			teacherRating = 4.2,
			isTranslatedCompletion = false,
		}
		for key, value in overrides do
			base[key] = value
		end
		return base
	end

	t.test("an honest completion pays", function()
		t.greaterThan(Economy.teacherPayout(input({})).amount, 0, "honest payout")
	end)

	t.test("a scripted completion pays nothing and says why", function()
		local result = Economy.teacherPayout(input({ actualSeconds = 1 }))
		t.equal(result.amount, 0, "scripted payout")
		t.equal(result.limitedBy, "engagement", "reason")
	end)

	t.test("the lifetime cap truncates rather than exceeding itself", function()
		local result = Economy.teacherPayout(input({
			lifetimePaidByThisStudent = Economy.LifetimePayoutCapPerStudent - 1,
		}))
		t.equal(result.amount, 1, "payout is trimmed to what remains")
		t.equal(result.limitedBy, "lifetimeCap", "reason")
	end)

	t.test("a student who has hit the cap is worth nothing further", function()
		local result = Economy.teacherPayout(input({
			lifetimePaidByThisStudent = Economy.LifetimePayoutCapPerStudent,
		}))
		t.equal(result.amount, 0, "payout after the cap")
	end)

	t.test("farming one student loses to teaching many", function()
		-- Ten completions from one student against one each from ten students.
		local farmed = 0
		local paid = 0
		for completion = 0, 9 do
			local result = Economy.teacherPayout(input({
				priorCompletions = completion,
				lifetimePaidByThisStudent = paid,
			}))
			farmed += result.amount
			paid += result.amount
		end

		local honest = Economy.teacherPayout(input({})).amount * 10
		t.lessThan(farmed, honest, "ten repeats against ten students")
	end)

	t.test("a translated completion pays the author a share, not the whole", function()
		local original = Economy.teacherPayout(input({})).amount
		local translated = Economy.teacherPayout(input({ isTranslatedCompletion = true })).amount
		t.near(translated, original * Economy.TranslatedReachShare, "translated share")
	end)

	t.suite("Economy: anti-alt gate")

	t.test("a fresh account does not count toward teacher income", function()
		t.isFalse(Economy.countsTowardTeacherPayout(0, 100000), "brand new account")
		t.isFalse(Economy.countsTowardTeacherPayout(365, 10), "old account, no playtime")
		t.isTrue(Economy.countsTowardTeacherPayout(30, 3600), "established player")
	end)

	t.suite("Economy: student reward")

	t.test("passing is worth more than the same answers without passing", function()
		local failed = Economy.studentReward(4, false, 1)
		local passing = Economy.studentReward(4, true, 1)
		t.greaterThan(passing, failed, "pass bonus")
	end)

	t.test("multipliers compound", function()
		local single = Economy.studentReward(6, true, 1)
		t.equal(Economy.studentReward(6, true, 2), single * 2, "doubled")
	end)
end
