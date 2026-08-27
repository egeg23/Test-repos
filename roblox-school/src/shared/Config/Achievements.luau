--!strict
--- Achievement branches, and the permanent perks their tiers hand out.
---
--- This is the "the more you play, the more you get" half of the design, and the
--- one system that has to be balanced against the other two lanes rather than on
--- its own terms. Three lanes reach the same power:
---
---   * pay        -- immediate, bounded by what is on sale;
---   * ads        -- slow, capped daily, closes most of the gap to paying;
---   * play       -- slowest, but permanent and unbounded by anything but time.
---
--- The design rule that keeps all three alive: perks are **broad, permanent and
--- slow**; passes are **immediate**. A veteran who never paid should out-earn a
--- newcomer who did, and a veteran who also pays should beat both. That is only
--- true if the perk ceiling sits below the pass multiplier, which is asserted at
--- the bottom of this file rather than left as an intention.
---
--- Engine-free like every config here: no Color3, no Enum, so the tests can run
--- these functions rather than a description of them.

local Achievements = {}

--- What a perk actually does. Every effect is a multiplier or an additive count
--- applied at one named place in the game, so a perk cannot mean two things.
export type Effect =
	"studentPoints" -- multiplier on what a lesson pays the student
	| "teacherPayout" -- multiplier on teaching income
	| "adReward" -- multiplier on what an ad grants
	| "obstacleTime" -- extra seconds on an obstacle run
	| "classCapacity" -- extra seats in a class you own
	| "lessonSlots" -- extra lessons per day
	| "attemptRefund" -- free retries per day

--- Effects that multiply, as opposed to those that add. Kept as data because
--- three different files need to know which is which, and a fourth that guessed
--- would be wrong in a way nothing catches.
Achievements.Multiplicative = {
	studentPoints = true,
	teacherPayout = true,
	adReward = true,
} :: { [string]: boolean }

export type Perk = { effect: Effect, value: number }

export type Tier = {
	--- The counter value that unlocks this tier.
	at: number,
	--- Points paid once, on unlock.
	points: number,
	--- The permanent perk. Every tier has one: a tier that only paid points
	--- would be a quest, and the point of a branch is that it changes the game.
	perk: Perk,
}

export type Branch = {
	id: string,
	--- The stat this branch counts. Stats live on the profile and are only ever
	--- incremented, so a branch can never regress.
	stat: string,
	--- Which half of the game this branch belongs to. A student never sees the
	--- teaching branches until they are licensed, and showing them a locked wall
	--- of them at grade one is how a first session ends.
	audience: "student" | "teacher" | "both",
	displayKey: string,
	tiers: { Tier },
}

--- Ten branches. Five a student meets in their first hour, five that only open
--- up later -- the shape matters more than the count: a player should always be
--- part-way through something, and never be looking at ten empty bars.
Achievements.Branches = {
	{
		id = "scholar",
		stat = "lessonsPassed",
		audience = "student",
		displayKey = "achv.scholar",
		tiers = {
			{ at = 10, points = 50, perk = { effect = "studentPoints", value = 1.02 } },
			{ at = 50, points = 150, perk = { effect = "studentPoints", value = 1.03 } },
			{ at = 150, points = 400, perk = { effect = "studentPoints", value = 1.04 } },
			{ at = 400, points = 1000, perk = { effect = "studentPoints", value = 1.05 } },
			{ at = 1000, points = 2500, perk = { effect = "studentPoints", value = 1.06 } },
		},
	},
	{
		id = "perfectionist",
		stat = "perfectLessons",
		audience = "student",
		displayKey = "achv.perfectionist",
		tiers = {
			{ at = 5, points = 80, perk = { effect = "studentPoints", value = 1.02 } },
			{ at = 25, points = 220, perk = { effect = "attemptRefund", value = 1 } },
			{ at = 100, points = 600, perk = { effect = "lessonSlots", value = 1 } },
			{ at = 300, points = 1600, perk = { effect = "attemptRefund", value = 2 } },
		},
	},
	{
		id = "athlete",
		stat = "coursesFinished",
		audience = "student",
		displayKey = "achv.athlete",
		tiers = {
			{ at = 5, points = 60, perk = { effect = "obstacleTime", value = 3 } },
			{ at = 25, points = 180, perk = { effect = "obstacleTime", value = 5 } },
			{ at = 100, points = 500, perk = { effect = "obstacleTime", value = 8 } },
			{ at = 300, points = 1400, perk = { effect = "obstacleTime", value = 12 } },
		},
	},
	{
		id = "polymath",
		stat = "subjectsMastered",
		audience = "student",
		displayKey = "achv.polymath",
		tiers = {
			{ at = 2, points = 100, perk = { effect = "lessonSlots", value = 1 } },
			{ at = 4, points = 300, perk = { effect = "studentPoints", value = 1.03 } },
			{ at = 6, points = 700, perk = { effect = "lessonSlots", value = 2 } },
			{ at = 8, points = 1800, perk = { effect = "adReward", value = 1.06 } },
		},
	},
	{
		id = "regular",
		stat = "longestStreak",
		audience = "both",
		displayKey = "achv.regular",
		tiers = {
			{ at = 3, points = 60, perk = { effect = "adReward", value = 1.05 } },
			{ at = 7, points = 200, perk = { effect = "studentPoints", value = 1.02 } },
			{ at = 30, points = 900, perk = { effect = "adReward", value = 1.1 } },
			{ at = 100, points = 3000, perk = { effect = "attemptRefund", value = 2 } },
		},
	},
	{
		id = "graduate",
		stat = "graduatedCount",
		audience = "both",
		displayKey = "achv.graduate",
		tiers = {
			{ at = 1, points = 500, perk = { effect = "studentPoints", value = 1.04 } },
			{ at = 2, points = 1200, perk = { effect = "teacherPayout", value = 1.04 } },
			{ at = 5, points = 3000, perk = { effect = "obstacleTime", value = 10 } },
			{ at = 10, points = 8000, perk = { effect = "teacherPayout", value = 1.06 } },
		},
	},
	{
		id = "mentor",
		stat = "studentsTaught",
		audience = "teacher",
		displayKey = "achv.mentor",
		tiers = {
			{ at = 10, points = 120, perk = { effect = "teacherPayout", value = 1.03 } },
			{ at = 50, points = 400, perk = { effect = "classCapacity", value = 2 } },
			{ at = 200, points = 1200, perk = { effect = "teacherPayout", value = 1.05 } },
			{ at = 750, points = 3500, perk = { effect = "classCapacity", value = 5 } },
		},
	},
	{
		id = "faculty",
		stat = "lessonsAuthored",
		audience = "teacher",
		displayKey = "achv.faculty",
		tiers = {
			{ at = 3, points = 100, perk = { effect = "teacherPayout", value = 1.02 } },
			{ at = 15, points = 350, perk = { effect = "teacherPayout", value = 1.03 } },
			{ at = 50, points = 1000, perk = { effect = "classCapacity", value = 3 } },
			{ at = 150, points = 3000, perk = { effect = "teacherPayout", value = 1.05 } },
		},
	},
	{
		id = "acclaimed",
		stat = "fiveStarRatings",
		audience = "teacher",
		displayKey = "achv.acclaimed",
		tiers = {
			{ at = 10, points = 200, perk = { effect = "teacherPayout", value = 1.02 } },
			{ at = 50, points = 700, perk = { effect = "teacherPayout", value = 1.04 } },
			{ at = 200, points = 2000, perk = { effect = "teacherPayout", value = 1.05 } },
		},
	},
	{
		id = "citizen",
		stat = "votesCast",
		audience = "both",
		displayKey = "achv.citizen",
		tiers = {
			{ at = 1, points = 40, perk = { effect = "adReward", value = 1.03 } },
			{ at = 5, points = 160, perk = { effect = "studentPoints", value = 1.02 } },
			{ at = 20, points = 600, perk = { effect = "adReward", value = 1.07 } },
		},
	},
} :: { Branch }

local byId: { [string]: Branch } = {}
for _, branch in Achievements.Branches do
	byId[branch.id] = branch
end

function Achievements.get(id: string): Branch?
	return byId[id]
end

--- The id a single unlocked tier is stored under. One string per tier rather
--- than a count, because a count cannot say *which* tiers were granted after a
--- branch's thresholds are retuned -- and retuning them is inevitable.
function Achievements.tierId(branchId: string, tierIndex: number): string
	return `{branchId}:{tierIndex}`
end

--- Every tier a stat value has reached, as ids. Pure, so granting is a set
--- difference against what the profile already holds rather than a scan with
--- side effects.
function Achievements.earned(branch: Branch, value: number): { string }
	local ids = {}
	for index, tier in branch.tiers do
		if value >= tier.at then
			table.insert(ids, Achievements.tierId(branch.id, index))
		end
	end
	return ids
end

--- What a set of unlocked tier ids adds up to for one effect.
---
--- Multiplicative effects compound; additive ones sum. Returns the identity for
--- the effect's kind when nothing is unlocked, so a caller never has to special
--- case a new player.
function Achievements.perkTotal(unlocked: { [string]: boolean }, effect: Effect): number
	local multiplicative = Achievements.Multiplicative[effect] == true
	local total = if multiplicative then 1 else 0
	for _, branch in Achievements.Branches do
		for index, tier in branch.tiers do
			if tier.perk.effect ~= effect then
				continue
			end
			if not unlocked[Achievements.tierId(branch.id, index)] then
				continue
			end
			if multiplicative then
				total *= tier.perk.value
			else
				total += tier.perk.value
			end
		end
	end
	return total
end

--- The most any player can ever reach, for balancing against the shop.
function Achievements.maxPerk(effect: Effect): number
	local all: { [string]: boolean } = {}
	for _, branch in Achievements.Branches do
		for index in branch.tiers do
			all[Achievements.tierId(branch.id, index)] = true
		end
	end
	return Achievements.perkTotal(all, effect)
end

--- Ceilings, checked rather than intended.
---
--- The x2 XP pass is the headline purchase. If a player who never paid could
--- reach x2 by grinding, the pass would be a shortcut to somewhere they were
--- going anyway, and the whole free lane would be a slow refund. Holding perks
--- under this keeps the pass worth buying at every point on the curve -- and the
--- two multiply, so the veteran who also pays is still ahead of both.
Achievements.MaxStudentPointsPerk = 1.75
Achievements.MaxTeacherPayoutPerk = 1.5
Achievements.MaxAdRewardPerk = 1.4

assert(
	Achievements.maxPerk("studentPoints") <= Achievements.MaxStudentPointsPerk,
	`student perks reach x{Achievements.maxPerk("studentPoints")}, over the {Achievements.MaxStudentPointsPerk} ceiling`
)
assert(
	Achievements.maxPerk("teacherPayout") <= Achievements.MaxTeacherPayoutPerk,
	`teacher perks reach x{Achievements.maxPerk("teacherPayout")}, over the {Achievements.MaxTeacherPayoutPerk} ceiling`
)
assert(
	Achievements.maxPerk("adReward") <= Achievements.MaxAdRewardPerk,
	`ad perks reach x{Achievements.maxPerk("adReward")}, over the {Achievements.MaxAdRewardPerk} ceiling`
)

--- The daily streak's own payout, separate from the `regular` branch it feeds.
---
--- The branch pays at three days, seven, thirty and a hundred. That leaves day
--- two paying nothing, which is exactly the day a habit is or is not formed. So
--- every day pays something, rising, and flattening: the curve has to reward
--- returning without making a missed day feel like a punishment worth quitting
--- over. A player on day forty is not earning four times a player on day ten.
Achievements.StreakRewardBase = 40
Achievements.StreakRewardPerDay = 12
Achievements.StreakRewardCapDay = 14

function Achievements.streakReward(day: number): number
	local counted = math.clamp(day, 1, Achievements.StreakRewardCapDay)
	return Achievements.StreakRewardBase + (counted - 1) * Achievements.StreakRewardPerDay
end

--- Thresholds must ascend, or a later tier unlocks before an earlier one and the
--- branch reads as broken to the only person who can see it.
for _, branch in Achievements.Branches do
	assert(#branch.tiers > 0, `branch "{branch.id}" has no tiers`)
	for index = 2, #branch.tiers do
		assert(
			branch.tiers[index].at > branch.tiers[index - 1].at,
			`branch "{branch.id}" tier {index} is not above tier {index - 1}`
		)
		assert(
			branch.tiers[index].points > branch.tiers[index - 1].points,
			`branch "{branch.id}" tier {index} pays no more than tier {index - 1}`
		)
	end
end

return Achievements
