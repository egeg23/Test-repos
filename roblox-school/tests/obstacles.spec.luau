--!strict
local Obstacles = require("../src/shared/Config/Obstacles")
local t = require("./harness")

return function()
	t.suite("Obstacles: difficulty curve")

	t.test("difficulty rises every single year", function()
		local previous = -1
		for grade = 1, Obstacles.MaxGrade do
			local value = Obstacles.difficulty(grade)
			t.greaterThan(value, previous, `difficulty at grade {grade}`)
			previous = value
		end
	end)

	t.test("the curve back-loads instead of running straight", function()
		-- A straight ramp would make the final year twice the middle one. The
		-- design wants it to be genuinely hard, not merely twice as long.
		local ratio = Obstacles.difficulty(Obstacles.MaxGrade) / Obstacles.difficulty(6)
		t.greaterThan(ratio, 2.2, "final year against the middle")
	end)

	t.test("the last year sits at the edge of what a character can do", function()
		local last = Obstacles.paramsForGrade(Obstacles.MaxGrade)
		-- A Roblox character clears roughly 20 studs at a run and is about 2 wide.
		t.greaterThan(last.gapStuds, 16, "final gap width")
		t.lessThan(last.beamWidth, 2, "final beam width")
		t.lessThan(last.vanishSeconds, 0.7, "final tile lifetime")
		t.equal(last.checkpointEvery, 0, "checkpoints in the final year")
	end)

	t.test("the first year is gentle", function()
		local first = Obstacles.paramsForGrade(1)
		t.lessThan(first.gapStuds, 6, "first gap width")
		t.greaterThan(first.beamWidth, 5, "first beam width")
		t.equal(first.checkpointEvery, 1, "a checkpoint every module")
	end)

	t.suite("Obstacles: the teacher's grade window")

	t.test("a final-year class cannot be given easy work", function()
		-- Stated absolutely on purpose. An earlier version asserted that the low
		-- end equalled MaxGrade minus the window, which is true whatever the
		-- window is -- it restated the implementation and would have watched the
		-- window widen to nine years without a word.
		local low, high = Obstacles.allowedGrades(Obstacles.MaxGrade)
		t.equal(high, Obstacles.MaxGrade, "clamped at the top")
		t.isTrue(low >= Obstacles.MaxGrade - 1, "a final year cannot be set below grade 10")
	end)

	t.test("the window is one year either side, not a corridor", function()
		local low, high = Obstacles.allowedGrades(6)
		t.equal(high - low, 2, "grades a mid-school class may choose between")
	end)

	t.test("a first-year class cannot be given a negative grade", function()
		local low = Obstacles.allowedGrades(1)
		t.equal(low, 1, "clamped at the bottom")
	end)

	t.suite("Obstacles: course validation")

	local function courseOf(grade: number, moduleIds: { string }): { string }
		local params = Obstacles.paramsForGrade(grade)
		local built = table.clone(moduleIds)
		local index = 1
		while #built < params.moduleCount do
			table.insert(built, moduleIds[index])
			index = index % #moduleIds + 1
		end
		return built
	end

	t.test("a well-formed course is accepted", function()
		local course = courseOf(5, { "gap", "narrowBeam", "movingPlatform", "vanishingTiles" })
		t.isTrue(Obstacles.validateCourse(5, 5, course).ok, "valid course")
	end)

	t.test("a grade outside the window is refused", function()
		local course = courseOf(1, { "gap", "narrowBeam" })
		local result = Obstacles.validateCourse(11, 1, course)
		t.isFalse(result.ok, "grade 1 course for an 11th grade class")
		t.equal(result.reason, "gradeOutOfWindow", "reason")
	end)

	t.test("a course shorter than its grade demands is refused", function()
		local result = Obstacles.validateCourse(5, 5, { "gap", "narrowBeam" })
		t.isFalse(result.ok, "two-module course")
		t.equal(result.reason, "tooShort", "reason")
	end)

	t.test("a course of one repeated module is refused", function()
		local params = Obstacles.paramsForGrade(8)
		local same = {}
		for _ = 1, params.moduleCount do
			table.insert(same, "gap")
		end
		local result = Obstacles.validateCourse(8, 8, same)
		t.isFalse(result.ok, "all identical modules")
		t.equal(result.reason, "tooRepetitive", "reason")
	end)

	t.test("a module above its grade is refused", function()
		local course = courseOf(2, { "gap", "narrowBeam", "hazardField" })
		local result = Obstacles.validateCourse(2, 2, course)
		t.isFalse(result.ok, "hazard field in a second-year course")
		t.equal(result.reason, "moduleTooAdvanced", "reason")
	end)

	t.test("every grade can satisfy its own variety rule", function()
		for grade = 1, Obstacles.MaxGrade do
			local available = #Obstacles.modulesForGrade(grade)
			local params = Obstacles.paramsForGrade(grade)
			local required = Obstacles.requiredDistinctTypes(grade, params.moduleCount)
			t.isTrue(available >= required, `grade {grade} has enough module types`)
		end
	end)
end
