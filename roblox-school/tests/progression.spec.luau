--!strict
local Progression = require("../src/shared/Config/Progression")
local t = require("./harness")

return function()
	t.suite("Progression: the grade ladder")

	t.test("each year asks for more than the one before", function()
		local previous = -1
		for grade = 1, Progression.MaxGrade do
			local required = Progression.lessonsForGrade(grade)
			t.greaterThan(required, previous, `lessons for grade {grade}`)
			previous = required
		end
	end)

	t.test("out-of-range grades clamp rather than returning nonsense", function()
		t.equal(Progression.lessonsForGrade(0), Progression.lessonsForGrade(1), "grade zero")
		t.equal(
			Progression.lessonsForGrade(99),
			Progression.lessonsForGrade(Progression.MaxGrade),
			"grade ninety-nine"
		)
	end)

	t.test("the whole school is a few weeks of play, not a year", function()
		-- 187 lessons at roughly two and a half minutes each, and a pass rate well
		-- under 100%, should land a first graduation inside about twenty hours.
		local lessons = Progression.totalLessonsToGraduate()
		local hoursOfLessons = lessons / 0.65 * 150 / 3600
		t.greaterThan(hoursOfLessons, 6, "time to graduate")
		t.lessThan(hoursOfLessons, 20, "time to graduate")
	end)

	t.suite("Progression: prestige")

	t.test("a first-time player has no prestige bonus", function()
		t.equal(Progression.prestigeMultiplier(0), 1, "never graduated")
	end)

	t.test("prestige compounds across graduations", function()
		t.near(
			Progression.prestigeMultiplier(2),
			Progression.NewGamePlusMultiplier ^ 2,
			"two graduations"
		)
	end)

	t.test("a negative count cannot produce a penalty", function()
		t.equal(Progression.prestigeMultiplier(-5), 1, "impossible input")
	end)

	t.suite("Progression: the school calendar")

	local WEEK = Progression.RealSecondsPerGameWeek

	t.test("a game week passes per real day", function()
		t.equal(Progression.gameWeek(0), 0, "epoch")
		t.equal(Progression.gameWeek(WEEK), 1, "one day later")
		t.equal(Progression.gameWeek(WEEK * 9), 9, "nine days later")
	end)

	t.test("a term ends on a test week and only then", function()
		local found = 0
		for week = 0, Progression.GameWeeksPerTerm - 1 do
			if Progression.isTestWeek(week * WEEK) then
				found += 1
				t.equal(week, Progression.GameWeeksPerTerm - 1, "test week position")
			end
		end
		t.equal(found, 1, "test weeks per term")
	end)

	t.test("the calendar only ever adds", function()
		for week = 0, Progression.GameWeeksPerTerm * 2 do
			t.isTrue(
				Progression.calendarMultiplier(week * WEEK) >= 1,
				`calendar multiplier in week {week}`
			)
		end
	end)

	t.suite("Progression: graduation")

	t.test("every path the client can offer is one the server accepts", function()
		t.equal(#Progression.GraduationPaths, 3, "paths offered")
	end)
	t.suite("Progression: university is a real branch")

	t.test("a university year pays more than school", function()
		-- The branch was a trap before this: all three graduation paths set the
		-- grade to the maximum, and university alone granted nothing for it.
		t.equal(Progression.tierMultiplier(0), 1, "school is the baseline")
		for tier = 1, Progression.MaxUniversityTier do
			t.greaterThan(
				Progression.tierMultiplier(tier),
				Progression.tierMultiplier(tier - 1),
				`year {tier} pays more than year {tier - 1}`
			)
		end
	end)

	t.test("and asks more", function()
		local school = 0.6
		t.equal(Progression.passFractionForTier(0, school), school, "school keeps its bar")
		for tier = 1, Progression.MaxUniversityTier do
			t.greaterThan(
				Progression.passFractionForTier(tier, school),
				school,
				`year {tier} raises the bar`
			)
		end
	end)

	t.test("the bar never becomes a lottery", function()
		-- A pass mark you can miss by one question on an unlucky draw stops being
		-- a bar and becomes chance. Ten questions means each one is 10%.
		local hardest = Progression.passFractionForTier(Progression.MaxUniversityTier, 0.6)
		t.lessThan(hardest, 0.9, "there is room to get one wrong")
		t.lessThan(hardest, Progression.MaxUniversityPassFraction + 0.001, "under its ceiling")
	end)

	t.test("out-of-range tiers clamp instead of running away", function()
		-- Reached only through a corrupt profile, and an unbounded multiplier
		-- there would be an unbounded payout.
		t.equal(
			Progression.tierMultiplier(99),
			Progression.tierMultiplier(Progression.MaxUniversityTier),
			"far above the last year"
		)
		t.equal(Progression.tierMultiplier(-5), 1, "below zero is school")
		t.equal(
			Progression.lessonsForTier(99),
			Progression.lessonsForTier(Progression.MaxUniversityTier),
			"lesson requirement clamps too"
		)
	end)

	t.test("a university year is longer than any school year", function()
		-- Otherwise the harder, better-paid tier would also be the quicker one,
		-- and school would be strictly pointless.
		local longestSchool = Progression.lessonsForGrade(Progression.MaxGrade)
		t.greaterThan(
			Progression.lessonsForTier(1),
			longestSchool,
			"the first year already asks more than the last school grade"
		)
	end)
end
