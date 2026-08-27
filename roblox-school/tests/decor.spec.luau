--!strict
--- The decor layer is data, so what is worth testing is that the lookups never
--- leave a caller without an answer. A builder that gets nil back does not draw
--- a plain room -- it errors halfway through the school and leaves the player on
--- a baseplate, which is the exact failure the world was built to end.

local Decor = require("../src/shared/Config/Decor")
local Authoring = require("../src/shared/Config/Authoring")
local t = require("./harness")

return function()

	t.suite("Decor: every room can be built")

	t.test("every declared theme is complete enough to build", function()
		-- Whether the *set* of themes covers the subject list is checked by
		-- tools/check_decor.py, which can read Subjects.luau -- this spec cannot,
		-- because that module requires through a Roblox instance path. What is
		-- checked here is the part that is pure: that each theme, once declared,
		-- has values a builder can use without guarding every field.
		local count = 0
		for id, theme in Decor.Subjects do
			count += 1
			t.isTrue(theme.props >= 0, `{id} has a prop count`)
			t.isTrue(theme.lightBrightness > 0, `{id} is lit`)
			t.isTrue(theme.floorMaterial ~= "", `{id} names a floor material`)
			-- Packed 0xRRGGBB, not a Color3: config is engine-free so these
			-- tests can run it at all, and a colour that leaked back to a
			-- Color3 would break standalone Luau on the next edit, not this one.
			t.isTrue(typeof(theme.wall) == "number", `{id} carries a packed colour`)
			t.isTrue(theme.wall >= 0 and theme.wall <= 0xFFFFFF, `{id} is in range`)
		end
		t.isTrue(count > 0, "there are themes at all")
	end)

	t.test("an unknown subject falls back rather than returning nil", function()
		-- A subject added to config before its theme exists must produce a plain
		-- room, not a crash partway through building the school.
		local theme = Decor.forSubject("astrophysics")
		t.isTrue(theme ~= nil, "there is always a theme")
		t.equal(theme.effect, Decor.Default.effect, "it is the default one")
	end)

	t.test("an unknown hall falls back too", function()
		t.equal(Decor.forHall("swimmingPool").effect, Decor.Default.effect, "falls back")
	end)

	t.suite("Decor: particle budget")

	t.test("no effect exceeds the live-particle cap", function()
		for name, _ in Decor.Emissions do
			local live = Decor.particleBudget(name)
			t.isTrue(
				live <= Decor.MaxLiveParticles,
				`{name} holds {live} particles, cap is {Decor.MaxLiveParticles}`
			)
		end
	end)

	t.test("an effect with no emission costs nothing", function()
		-- "none" is a real value in the theme table, and asking its budget must
		-- answer zero rather than erroring: the builder asks before it decides
		-- whether to create an emitter at all.
		t.equal(Decor.particleBudget("none"), 0, "no emitter, no particles")
	end)

	t.test("every effect a theme names has an emission", function()
		local named: { [string]: boolean } = {}
		for _, theme in Decor.Subjects do
			named[theme.effect] = true
		end
		for _, theme in Decor.Halls do
			named[theme.effect] = true
		end
		for effect in named do
			t.isTrue(
				effect == "none" or Decor.Emissions[effect] ~= nil,
				`effect "{effect}" is defined`
			)
		end
	end)

	t.suite("Decor: grade tiers")

	t.test("every playable grade belongs to exactly one tier", function()
		for grade = Authoring.MinGrade, Authoring.MaxGrade do
			local matches = 0
			for _, tier in Decor.Tiers do
				if grade >= tier.minGrade and grade <= tier.maxGrade then
					matches += 1
				end
			end
			t.equal(matches, 1, `grade {grade} is in one tier`)
		end
	end)

	t.test("tiers get colder as the grades get higher", function()
		-- The design claim is that the school visibly hardens as a student
		-- climbs. If warmth stopped decreasing, the tiers would still all
		-- resolve and the claim would quietly stop being true.
		for index = 2, #Decor.Tiers do
			t.isTrue(
				Decor.Tiers[index].warmth < Decor.Tiers[index - 1].warmth,
				`{Decor.Tiers[index].id} is colder than {Decor.Tiers[index - 1].id}`
			)
		end
	end)

	t.test("a grade outside the range clamps to an end tier", function()
		-- Reached only through a progression bug, and a crash in the decor layer
		-- would hide the real one.
		t.equal(Decor.tierFor(0).id, Decor.Tiers[1].id, "below the first grade")
		t.equal(
			Decor.tierFor(Authoring.MaxGrade + 5).id,
			Decor.Tiers[#Decor.Tiers].id,
			"above the last grade"
		)
	end)
end
