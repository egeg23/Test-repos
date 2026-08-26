--!strict
local Campus = require("../src/shared/Config/Campus")
local t = require("./harness")

return function()
	local DAY = Campus.SecondsPerDay
	local function at(day: number, second: number?): number
		return Campus.Epoch + day * DAY + (second or 0)
	end

	t.suite("Campus: the election calendar")

	t.test("phases partition the cycle with no gap and no overlap", function()
		local counts = { term = 0, campaign = 0, voting = 0 }
		for day = 0, Campus.CycleDays - 1 do
			counts[Campus.phase(at(day))] += 1
		end
		t.equal(counts.term, Campus.CampaignStartDay, "term days")
		t.equal(
			counts.campaign,
			Campus.VotingStartDay - Campus.CampaignStartDay,
			"campaign days"
		)
		t.equal(counts.voting, Campus.CycleDays - Campus.VotingStartDay, "voting days")
	end)

	t.test("a phase holds for the whole of its last day", function()
		-- Every server derives the phase independently, so an off-by-one here does
		-- not fail loudly: it means two servers disagree about whether voting is
		-- open, and votes sometimes count.
		t.equal(Campus.phase(at(Campus.CampaignStartDay - 1, DAY - 1)), "term", "last term second")
		t.equal(Campus.phase(at(Campus.VotingStartDay - 1, DAY - 1)), "campaign", "last campaign second")
		t.equal(Campus.phase(at(Campus.CycleDays - 1, DAY - 1)), "voting", "last voting second")
	end)

	t.test("voting hands straight over to a new term", function()
		local last = at(Campus.CycleDays - 1, DAY - 1)
		t.equal(Campus.phase(last), "voting", "final second of the cycle")
		t.equal(Campus.phase(last + 1), "term", "first second of the next")
		t.equal(Campus.cycleIndex(last), 0, "cycle before")
		t.equal(Campus.cycleIndex(last + 1), 1, "cycle after")
	end)

	t.test("the day index resets with the cycle", function()
		t.equal(Campus.dayInCycle(at(Campus.CycleDays)), 0, "first day of the next cycle")
		t.equal(Campus.dayInCycle(at(Campus.CycleDays + 3)), 3, "fourth day of the next cycle")
	end)

	t.suite("Campus: voting weight")

	t.test("a new voter counts once", function()
		t.equal(Campus.voteWeight(0), 1, "no playtime")
	end)

	t.test("weight rises with time played and then stops", function()
		t.greaterThan(Campus.voteWeight(24 * 3600), Campus.voteWeight(3600), "a day against an hour")
		t.equal(Campus.voteWeight(10 ^ 9), Campus.VoteWeightCap, "capped")
	end)

	t.test("an hour of play does not already max out the weight", function()
		-- This caught a real bug: the checker read `12 * 3600` as 12 and reported
		-- everything fine while the cap was reached after an hour.
		t.lessThan(Campus.voteWeight(3600), Campus.VoteWeightCap, "one hour")
	end)

	t.suite("Campus: eligibility")

	t.test("fresh accounts cannot vote", function()
		t.isFalse(Campus.canVote(0, 10 ^ 6), "brand new account")
		t.isFalse(Campus.canVote(365, 0), "old account that has not played")
		t.isTrue(Campus.canVote(30, Campus.MinPlaySecondsToVote), "established player")
	end)

	t.suite("Campus: the office only adds")

	t.test("every multiplier the director controls is at least one", function()
		t.isTrue(Campus.SubjectOfMonthMultiplier >= 1, "subject of the month")
		t.isTrue(Campus.EventMultiplier >= 1, "school event")
	end)

	t.test("the director's cut is too small to be worth farming", function()
		t.lessThan(Campus.DirectorShare, 0.1, "director share")
		t.isTrue(Campus.DirectorShare >= 0, "director share is not negative")
	end)

	t.test("only mottos from the list are accepted", function()
		t.isTrue(Campus.isMotto(Campus.Mottos[1]), "a listed motto")
		t.isFalse(Campus.isMotto("motto.anythingIWant"), "an invented one")
	end)
end
