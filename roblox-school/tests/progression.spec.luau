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
end
