--!strict
--- The weekly Squish Show.
---
--- Each week every player's collection gets a score, and the best of the week
--- win a badge and that season's squish. The score counts only the best few
--- squishes a player owns, so the show rewards a good collection rather than a
--- big pile of commons, and a player cannot farm it by hoarding duplicates.

local Types = require(script.Parent.Parent.Types)
local Squishes = require(script.Parent.Squishes)

local Show = {}

Show.CountedSquishes = 10
Show.Winners = 10
--- Points double per tier, slower than income grows: a tier-5 is worth showing
--- off, but ten different rares should still be able to beat one giant common.
Show.TierPointsMultiplier = 2

--- Weeks start Monday 00:00 UTC. The Unix epoch fell on a Thursday, so the
--- first Monday is four days later.
Show.EpochMonday = 4 * 86400
Show.WeekSeconds = 7 * 86400

function Show.weekIndex(timestamp: number): number
	return math.floor((timestamp - Show.EpochMonday) / Show.WeekSeconds)
end

function Show.weekStart(week: number): number
	return Show.EpochMonday + week * Show.WeekSeconds
end

function Show.points(squish: Types.Squish): number
	local species = Squishes.get(squish.species)
	if species == nil then
		return 0
	end
	return Squishes.Rarities[species.rarity].showPoints * Show.TierPointsMultiplier ^ (squish.tier - 1)
end

--- Score for a collection: the sum of the best CountedSquishes.
function Show.score(squishes: { [string]: Types.Squish }): number
	local points: { number } = {}
	for _, squish in squishes do
		table.insert(points, Show.points(squish))
	end
	table.sort(points, function(a, b)
		return a > b
	end)
	local total = 0
	for index = 1, math.min(#points, Show.CountedSquishes) do
		total += points[index]
	end
	return math.floor(total)
end

return Show
