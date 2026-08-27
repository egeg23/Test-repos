--!strict
local Authoring = require("../src/shared/Config/Authoring")
local t = require("./harness")

return function()
	local function draft(overrides: { [string]: any }): any
		local base: any = {
			subject = "math",
			grade = 5,
			stem = "Половина числа равна 8. Чему равно само число?",
			options = { "4", "8", "16", "12" },
			answer = 3,
			explanation = "Если половина это 8, то целое вдвое больше: 8 × 2 = 16.",
		}
		for key, value in overrides do
			base[key] = value
		end
		return base
	end

	t.suite("Authoring: a well-formed question")

	t.test("a good draft passes", function()
		t.isTrue(Authoring.validate(draft({})).ok, "reference draft")
	end)

	t.suite("Authoring: each rule refuses its own violation")

	local cases = {
		{ name = "a stem barely there", override = { stem = "Что?" }, reason = "stemTooShort" },
		{
			name = "a stem past the limit",
			override = { stem = string.rep("a", Authoring.MaxStemChars + 1) },
			reason = "stemTooLong",
		},
		{
			name = "three options instead of four",
			override = { options = { "1", "2", "3" } },
			reason = "optionCount",
		},
		{
			name = "an answer index outside the options",
			override = { answer = 5 },
			reason = "badAnswer",
		},
		{
			name = "two options that are the same",
			override = { options = { "4", "8", "16", "16" } },
			reason = "duplicateOption",
		},
		{
			name = "an empty option",
			override = { options = { "4", "", "16", "12" } },
			reason = "emptyOption",
		},
		{
			name = "one option far longer than the rest",
			override = {
				options = { "4", "8", "12", "шестнадцать, потому что восемь умножить на два" },
			},
			reason = "lopsidedOptions",
		},
		{
			name = "an explanation that explains nothing",
			override = { explanation = "потому что" },
			reason = "explanationTooShort",
		},
		{
			name = "a grade that is not a school year",
			override = { grade = 14 },
			reason = "badGrade",
		},
	}

	for _, case in cases do
		t.test(case.name .. " is refused", function()
			local result = Authoring.validate(draft(case.override))
			t.isFalse(result.ok, case.name)
			t.equal(result.reason, case.reason, "reason")
		end)
	end

	t.suite("Authoring: the lopsided-option rule")

	t.test("options of similar length are fine", function()
		t.isTrue(
			Authoring.validate(draft({
				options = { "Красный", "Зелёный", "Синий", "Жёлтый" },
			})).ok,
			"four similar options"
		)
	end)

	t.test("the rule measures against the average, not the shortest", function()
		-- Otherwise a single one-character option would condemn every question
		-- that has one, which is most numeric questions.
		t.isTrue(
			Authoring.validate(draft({ options = { "1", "2", "16", "100" } })).ok,
			"numeric options of differing digits"
		)
	end)

	t.suite("Authoring: character counting")

	t.test("length is counted in characters, not bytes", function()
		-- Cyrillic is two bytes per character. Counting bytes would give a Russian
		-- question half the allowance of an English one.
		local stem = string.rep("я", Authoring.MaxStemChars)
		t.isTrue(Authoring.validate(draft({ stem = stem })).ok, "a stem exactly at the limit")
		t.isFalse(
			Authoring.validate(draft({ stem = stem .. "я" })).ok,
			"a stem one character over"
		)
	end)
	t.suite("Authoring: ad-eligibility switch")

	t.test("free text is a switch, and the rest of authoring does not depend on it", function()
		-- The switch exists so the experience can be made unambiguously ads-eligible
		-- (Roblox requires "no free-form user creation") without losing the bank,
		-- prefab courses or assembly tasks. This test guards the two things that
		-- would quietly break that: the flag disappearing, and the structural rules
		-- starting to consult it.
		t.isTrue(typeof(Authoring.FreeTextEnabled) == "boolean", "the flag exists and is a boolean")

		local before = Authoring.FreeTextEnabled
		Authoring.FreeTextEnabled = false
		t.isTrue(
			Authoring.validate(draft({})).ok,
			"validate() judges structure only -- the switch is enforced at the service, not here"
		)
		Authoring.FreeTextEnabled = before
	end)
end
