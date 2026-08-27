--!strict
--- The branch config is where the free lane's power is decided, so what is worth
--- testing is the arithmetic that keeps it from swallowing the paid one -- and
--- the granting logic, which is the only part that could pay twice.

local Achievements = require("../src/shared/Config/Achievements")
local Economy = require("../src/shared/Config/Economy")
local t = require("./harness")

return function()
	t.suite("Achievements: the three lanes stay distinct")

	t.test("perks never reach the double-XP pass", function()
		-- The whole free lane is a slow refund if grinding gets you where the
		-- pass gets you. The ceiling is what stops that, and this is the claim
		-- the ceiling exists to make.
		local perk = Achievements.maxPerk("studentPoints")
		t.lessThan(perk, 2, "a full clear is worth less than the x2 pass")
		t.lessThan(perk, Achievements.MaxStudentPointsPerk, "and stays under its own ceiling")
	end)

	t.test("teacher and ad perks stay under their ceilings", function()
		t.lessThan(
			Achievements.maxPerk("teacherPayout"),
			Achievements.MaxTeacherPayoutPerk,
			"teacher payout"
		)
		t.lessThan(Achievements.maxPerk("adReward"), Achievements.MaxAdRewardPerk, "ad reward")
	end)

	t.test("a full clear is still worth having", function()
		-- The opposite failure: perks so cautious that the branches are
		-- decoration. A veteran should be meaningfully ahead of a newcomer.
		t.greaterThan(Achievements.maxPerk("studentPoints"), 1.2, "student points")
		t.greaterThan(Achievements.maxPerk("teacherPayout"), 1.2, "teacher payout")
	end)

	t.test("the capacity perk does not outgrow the capacity pass", function()
		-- Both add seats. If the earned one is larger the pass is a downgrade,
		-- which is the same trap the fill-rate factor already had once.
		t.lessThan(
			Achievements.maxPerk("classCapacity"),
			Economy.CapacityPassBonus + 1,
			"earned seats do not exceed the bought ones"
		)
	end)

	t.suite("Achievements: earning")

	t.test("a stat earns every tier at or below it, and no more", function()
		local branch = Achievements.get("scholar")
		t.isTrue(branch ~= nil, "the scholar branch exists")
		t.equal(#Achievements.earned(branch, 0), 0, "nothing at zero")
		t.equal(#Achievements.earned(branch, 9), 0, "nothing just below the first")
		t.equal(#Achievements.earned(branch, 10), 1, "exactly at the first")
		t.equal(#Achievements.earned(branch, 49), 1, "still one below the second")
		t.equal(#Achievements.earned(branch, 10000), #branch.tiers, "all of them, far past the last")
	end)

	t.test("earning is idempotent", function()
		-- Granting is a set difference against what the profile holds, so the ids
		-- for a given value must be stable. If they were not, the same tier would
		-- be paid on every lesson.
		local branch = Achievements.get("athlete")
		local first = Achievements.earned(branch, 30)
		local second = Achievements.earned(branch, 30)
		t.equal(#first, #second, "same count")
		for index, id in first do
			t.equal(second[index], id, `id {index} is stable`)
		end
	end)

	t.suite("Achievements: perk totals")

	t.test("an empty profile gets the identity, not zero", function()
		-- A new player's multiplier must be 1. Returning 0 here would silently
		-- zero every reward in the game.
		t.equal(Achievements.perkTotal({}, "studentPoints"), 1, "multiplier identity")
		t.equal(Achievements.perkTotal({}, "lessonSlots"), 0, "count identity")
	end)

	t.test("multiplicative effects compound and additive ones sum", function()
		local unlocked = {
			[Achievements.tierId("scholar", 1)] = true,
			[Achievements.tierId("scholar", 2)] = true,
		}
		local branch = Achievements.get("scholar")
		local expected = branch.tiers[1].perk.value * branch.tiers[2].perk.value
		t.near(Achievements.perkTotal(unlocked, "studentPoints"), expected, "two tiers compound")

		local seats = {
			[Achievements.tierId("mentor", 2)] = true,
			[Achievements.tierId("mentor", 4)] = true,
		}
		local mentor = Achievements.get("mentor")
		t.equal(
			Achievements.perkTotal(seats, "classCapacity"),
			mentor.tiers[2].perk.value + mentor.tiers[4].perk.value,
			"two tiers sum"
		)
	end)

	t.test("a locked tier contributes nothing", function()
		t.equal(
			Achievements.perkTotal({ ["scholar:1"] = false }, "studentPoints"),
			1,
			"false is not unlocked"
		)
	end)

	t.suite("Achievements: branch shape")

	t.test("every branch is reachable and ascending", function()
		for _, branch in Achievements.Branches do
			t.isTrue(#branch.tiers > 0, `{branch.id} has tiers`)
			t.isTrue(branch.stat ~= "", `{branch.id} names a stat`)
			for index = 2, #branch.tiers do
				t.greaterThan(
					branch.tiers[index].at,
					branch.tiers[index - 1].at,
					`{branch.id} tier {index} threshold`
				)
			end
		end
	end)

	t.test("the first tier of a student branch is reachable in a session", function()
		-- A branch whose first tier takes a week is invisible to the players who
		-- decide whether there is a game here at all.
		for _, branch in Achievements.Branches do
			if branch.audience == "student" then
				t.lessThan(branch.tiers[1].at, 11, `{branch.id} opens early`)
			end
		end
	end)
	t.suite("Achievements: the daily streak")

	t.test("every day pays something, rising", function()
		-- Day two is where a habit is or is not formed, and the branch pays
		-- nothing until day three. So the curve has to cover it.
		for day = 1, 10 do
			t.greaterThan(Achievements.streakReward(day), 0, `day {day} pays`)
			if day > 1 then
				t.greaterThan(
					Achievements.streakReward(day),
					Achievements.streakReward(day - 1),
					`day {day} beats day {day - 1}`
				)
			end
		end
	end)

	t.test("the curve flattens rather than running away", function()
		-- A player on day forty must not be earning several times what a player
		-- on day ten earns, or a missed day becomes a reason to stop playing
		-- rather than a reason to come back tomorrow.
		local capped = Achievements.streakReward(Achievements.StreakRewardCapDay)
		t.equal(Achievements.streakReward(500), capped, "far past the cap pays the cap")
		t.lessThan(capped / Achievements.streakReward(1), 5, "a long streak is not a different game")
	end)

	t.test("day zero and negative days do not pay more than day one", function()
		-- Reached only through a clock going backwards, which it does: a server
		-- in a different region, a profile restored from a backup.
		t.equal(Achievements.streakReward(0), Achievements.streakReward(1), "day zero")
		t.equal(Achievements.streakReward(-5), Achievements.streakReward(1), "negative")
	end)
end
