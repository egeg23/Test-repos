--!strict
--- The election cycle and what a director may do with the office.
---
--- Phases are derived from the clock rather than driven by a scheduler. Roblox
--- has no reliable cron, and a scheduler would mean one server owning the
--- transition and the whole campus stalling when it dies. Deriving the phase from
--- `os.time()` means every server independently agrees what day it is, and the
--- only thing needing coordination is counting the votes once -- which is a
--- single conditional write.

local Campus = {}

--- Anchor for the cycle. A fixed point in the past so every server computes the
--- same cycle index; changing it would shift every campus's calendar at once.
Campus.Epoch = 1767225600 -- 2026-01-01T00:00:00Z

Campus.SecondsPerDay = 86400
Campus.CycleDays = 30
Campus.CampaignStartDay = 23
Campus.VotingStartDay = 28

export type Phase = "term" | "campaign" | "voting"

function Campus.cycleIndex(now: number): number
	return math.floor((now - Campus.Epoch) / (Campus.CycleDays * Campus.SecondsPerDay))
end

function Campus.dayInCycle(now: number): number
	local elapsed = (now - Campus.Epoch) % (Campus.CycleDays * Campus.SecondsPerDay)
	return math.floor(elapsed / Campus.SecondsPerDay)
end

function Campus.phase(now: number): Phase
	local day = Campus.dayInCycle(now)
	if day >= Campus.VotingStartDay then
		return "voting"
	elseif day >= Campus.CampaignStartDay then
		return "campaign"
	end
	return "term"
end

--- Who may stand. A director runs a campus for a month, so the bar is a teacher
--- with a track record rather than whoever happens to be online.
Campus.MinRatingToStand = 3.5
Campus.MinRatingCountToStand = 10
Campus.MaxConsecutiveTerms = 2

--- Who may vote, and for how much. Weight rises with time played and is capped,
--- so an organised group of real players outvotes a pile of fresh alts -- which
--- is the only outcome that keeps an election worth holding.
Campus.MinPlaySecondsToVote = 1800
Campus.MinAccountAgeDaysToVote = 7
Campus.VoteWeightCap = 4
Campus.SecondsPerExtraVoteWeight = 12 * 3600

function Campus.voteWeight(playSeconds: number): number
	local extra = playSeconds / Campus.SecondsPerExtraVoteWeight
	return math.clamp(1 + extra, 1, Campus.VoteWeightCap)
end

function Campus.canVote(accountAgeDays: number, playSeconds: number): boolean
	return accountAgeDays >= Campus.MinAccountAgeDaysToVote
		and playSeconds >= Campus.MinPlaySecondsToVote
end

--- Everything the office can do is a bonus it hands out. Nothing here takes
--- anything away from anyone.
---
--- That is not politeness, it is the only design that survives contact with a
--- twelve-year-old who wins an election and decides to be funny. A director who
--- could nerf a rival subject, demote a teacher or close a class would do all
--- three within a day. A director who can only choose who to boost can, at
--- worst, boost the wrong thing for a month.
Campus.SubjectOfMonthMultiplier = 1.5
Campus.EventMultiplier = 1.25
Campus.EventDurationSeconds = 3600
Campus.EventsPerTerm = 2
--- Share of points earned across the campus that reaches the director, paid out
--- of thin air rather than out of anyone's earnings.
Campus.DirectorShare = 0.02

Campus.Mottos = {
	"motto.learnTogether",
	"motto.noOneLeftBehind",
	"motto.askWhy",
	"motto.tryAgain",
	"motto.knowledgeIsPower",
	"motto.everyDayCounts",
}

function Campus.isMotto(key: string): boolean
	for _, candidate in Campus.Mottos do
		if candidate == key then
			return true
		end
	end
	return false
end

return Campus
