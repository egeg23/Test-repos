--!strict
local Show = require("../src/shared/Config/Show")
local Squishes = require("../src/shared/Config/Squishes")
local Trade = require("../src/shared/Config/Trade")
local t = require("./harness")

local function collection(list: { { any } }): { [string]: any }
	local result: { [string]: any } = {}
	for index, entry in list do
		local uid = `u{index}`
		result[uid] = { uid = uid, species = entry[1], tier = entry[2], origin = entry[3] or "box", obtainedAt = entry[4] or 0 }
	end
	return result
end

return function()
	t.suite("Show: scoring and the calendar")

	t.test("weeks start on a Monday", function()
		-- 2026-11-02 00:00 UTC is a Monday.
		local monday = 1793577600
		t.equal(os.date("!%A", monday), "Monday", "fixture is a Monday")
		local week = Show.weekIndex(monday)
		t.equal(Show.weekStart(week), monday, "week starts at Monday midnight")
		t.equal(Show.weekIndex(monday - 1), week - 1, "Sunday 23:59:59 is the previous week")
	end)

	t.test("only the best squishes count, so hoarding commons does not win", function()
		local hoard: { { any } } = {}
		for _ = 1, 60 do
			table.insert(hoard, { "dumpling", 1 })
		end
		local small = collection({ { "pandaBao", 1 } })
		t.lessThan(Show.score(collection(hoard)), Show.score(small), "sixty commons vs one epic")
	end)

	t.test("ten different rares beat one giant common", function()
		local rares: { { any } } = {}
		for _ = 1, 10 do
			table.insert(rares, { "boba", 1 })
		end
		local giant = collection({ { "dumpling", 5 } })
		t.greaterThan(Show.score(collection(rares)), Show.score(giant), "rares vs tier-5 common")
	end)

	t.test("every season has a prize squish that boxes cannot drop", function()
		for _, season in { "autumn", "winter", "spring", "summer" } do
			local species = Squishes.seasonalFor(season :: any)
			assert(species ~= nil, `{season} has a prize`)
			t.equal(species.season, season, "prize season")
		end
		t.equal(Squishes.seasonAt(1793577600), "autumn", "November is autumn")
	end)

	t.suite("Trade: rules")

	t.test("an honest offer passes", function()
		local owned = collection({ { "mochi", 1 }, { "boba", 2 } })
		t.isTrue((Trade.validateOffer({ "u1", "u2" }, owned, 1e6)), "offer")
	end)

	t.test("offers cannot repeat, overreach or include what is not yours", function()
		local owned = collection({ { "mochi", 1 }, { "boba", 1 }, { "toast", 1 }, { "frog", 1 }, { "cloud", 1 } })
		t.equal(select(2, Trade.validateOffer({ "u1", "u1" }, owned, 1e6)), "duplicate", "duplicate")
		t.equal(select(2, Trade.validateOffer({ "u1", "u2", "u3", "u4", "u5" }, owned, 1e6)), "tooMany", "too many")
		t.equal(select(2, Trade.validateOffer({ "nope" }, owned, 1e6)), "notOwned", "not owned")
	end)

	t.test("a freshly stolen squish cannot be passed straight on", function()
		local now = 1e6
		local owned = collection({ { "mochi", 1, "stolen", now - 60 } })
		t.equal(select(2, Trade.validateOffer({ "u1" }, owned, now)), "fresh", "fresh theft")
		local settled = collection({ { "mochi", 1, "stolen", now - Trade.FreshLockSeconds } })
		t.isTrue((Trade.validateOffer({ "u1" }, settled, now)), "settled theft")
	end)

	t.test("new accounts cannot trade", function()
		t.equal(select(2, Trade.canTrade(Trade.MinPlaySeconds - 1, 0, 1e6)), "tooNew", "new")
		t.isTrue((Trade.canTrade(Trade.MinPlaySeconds, 0, 1e6)), "old enough")
	end)
end
