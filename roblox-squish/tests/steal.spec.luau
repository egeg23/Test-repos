--!strict
local Steal = require("../src/shared/Config/Steal")
local t = require("./harness")

local function victim(overrides: { [string]: any }?): Steal.VictimState
	local state: { [string]: any } = {
		playSeconds = 3600,
		forfeitedProtection = false,
		shelved = 5,
		shieldUntil = 0,
		lossesToday = 0,
		online = true,
	}
	for key, value in overrides or {} do
		state[key] = value
	end
	return state :: any
end

return function()
	t.suite("Steal: who can be robbed")

	t.test("an ordinary base can be robbed", function()
		t.isTrue((Steal.canBeRobbed(victim(), 1000)), "ordinary")
	end)

	t.test("a new player is protected", function()
		local ok, reason = Steal.canBeRobbed(victim({ playSeconds = Steal.NewbieProtectionSeconds - 1 }), 1000)
		t.isFalse(ok, "newbie")
		t.equal(reason, "newbie", "reason")
	end)

	t.test("a new player who steals gives up protection", function()
		local state = victim({ playSeconds = 10, forfeitedProtection = true })
		t.isTrue((Steal.canBeRobbed(state, 1000)), "forfeited")
	end)

	t.test("the last squish on a shelf is never taken", function()
		local ok, reason = Steal.canBeRobbed(victim({ shelved = 1 }), 1000)
		t.isFalse(ok, "one left")
		t.equal(reason, "lastSquish", "reason")
		t.isTrue((Steal.canBeRobbed(victim({ shelved = Steal.ProtectedFavourites + 1 }), 1000)), "one beyond the favourites")
	end)

	t.test("a shield holds until it runs out", function()
		t.isFalse((Steal.canBeRobbed(victim({ shieldUntil = 1001 }), 1000)), "shielded")
		t.isTrue((Steal.canBeRobbed(victim({ shieldUntil = 1000 }), 1000)), "expired")
	end)

	t.test("the daily loss cap closes the base", function()
		t.isFalse((Steal.canBeRobbed(victim({ lossesToday = Steal.DailyLossCap }), 1000)), "capped")
	end)

	t.test("nobody is robbed while away", function()
		t.isFalse((Steal.canBeRobbed(victim({ online = false }), 1000)), "offline")
	end)

	t.test("the favourites are the most valuable squishes, ties settled the same way everywhere", function()
		local entries = {
			{ uid = "a", income = 4 },
			{ uid = "b", income = 60 },
			{ uid = "c", income = 15 },
			{ uid = "d", income = 15 },
			{ uid = "e", income = 1 },
		}
		local favourites = Steal.favourites(entries)
		local count = 0
		for _ in favourites do
			count += 1
		end
		t.equal(count, Steal.ProtectedFavourites, "how many are protected")
		t.isTrue(favourites.b == true, "the best is protected")
		t.isTrue(favourites.e == nil, "the worst is not")
		t.isTrue(favourites.c == true and favourites.d == true, "a tie at the cut is settled by uid")
		t.isTrue(next(Steal.favourites({})) == nil, "empty shelf")
	end)

	t.test("a base with nothing but favourites cannot be robbed", function()
		local ok, reason = Steal.canBeRobbed(victim({ shelved = Steal.ProtectedFavourites }), 1000)
		t.isFalse(ok, "only favourites")
		t.equal(reason, "lastSquish", "reason")
	end)

	t.suite("Steal: carrying")

	t.test("carrying is slower than walking and heavier squishes are slower still", function()
		t.lessThan(Steal.carrySpeed(1), Steal.NormalWalkSpeed, "carry slower than walk")
		for tier = 2, 5 do
			t.isTrue(Steal.carrySpeed(tier) <= Steal.carrySpeed(tier - 1), `tier {tier} not faster`)
			t.greaterThan(Steal.carrySpeed(tier), 0, `tier {tier} moves`)
		end
	end)

	t.test("slipping is likely over a long carry but not over a short one", function()
		t.greaterThan(Steal.holdProbability(1, 5), 0.8, "short carry usually holds")
		t.lessThan(Steal.holdProbability(5, 30), 0.25, "long heavy carry usually slips")
	end)
end
