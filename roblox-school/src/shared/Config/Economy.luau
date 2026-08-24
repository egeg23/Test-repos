--!strict
--- Teacher payout and the anti-abuse constants that keep it solvable.
---
--- Every factor here exists because of a specific way a two-sided economy gets
--- farmed. They are pure functions with no Roblox dependency so that
--- tools/simulate_economy.py can mirror them exactly and the balance can be
--- argued about with numbers instead of opinions.

local Economy = {}

Economy.BasePayout = 10

--- Repeat completions by the same student decay geometrically. Without this, a
--- teacher and four friends are a perpetual income machine.
Economy.UniquenessDecay = 0.6
Economy.UniquenessFloor = 0.05

--- Hard ceiling on what any single student can ever be worth to any single
--- teacher. The decay above slows farming; this ends it.
Economy.LifetimePayoutCapPerStudent = 400

Economy.EngagementMin = 0.5
Economy.EngagementMax = 1.25
--- Below this share of the expected time the completion is not fast, it is
--- automated, and pays nothing.
Economy.EngagementInvalidBelow = 0.15

--- Target band for a test's global pass rate.
Economy.QualityBandLow = 0.55
Economy.QualityBandHigh = 0.75
--- The band is deliberately asymmetric. A test everyone passes in seconds is the
--- farming exploit, so it collapses to near nothing. A test that is too hard is
--- merely bad teaching, so it is discouraged, not destroyed.
Economy.QualityFloorTooEasy = 0.15
Economy.QualityFloorTooHard = 0.5

--- A full class pays more per student than a half-empty one. This is what makes
--- a teacher want to recruit, and what makes capacity worth buying.
Economy.FillRateMin = 0.7
Economy.FillRateSpan = 0.6

Economy.RatingMin = 0.8
Economy.RatingSpan = 0.4
Economy.MaxRating = 5

--- A completion of a machine-translated copy pays the original author a share.
--- Writing something universally useful should be worth more than writing for
--- one locale.
Economy.TranslatedReachShare = 0.5

--- A student only counts toward teacher income once the account is old enough
--- and has played enough to not be a freshly minted alt.
Economy.MinAccountAgeDaysToCount = 3
Economy.MinPlaySecondsToCount = 900

--- What share of a paying player's benefit a fully ad-watching free player
--- reaches. The whole two-lane promise -- pay, or watch ads and catch up --
--- lives in this one number, so it is a constant to be tuned against retention,
--- not a value scattered through the reward tables.
Economy.AdCatchUpTarget = 0.55

export type PayoutInput = {
	--- Times this student already completed this teacher's lessons.
	priorCompletions: number,
	lifetimePaidByThisStudent: number,
	actualSeconds: number,
	expectedSeconds: number,
	globalPassRate: number,
	classMembers: number,
	classCapacity: number,
	teacherRating: number,
	isTranslatedCompletion: boolean,
}

export type PayoutBreakdown = {
	amount: number,
	uniqueness: number,
	engagement: number,
	quality: number,
	fill: number,
	rating: number,
	reach: number,
	--- Set when a cap or gate reduced the payout, for analytics and for showing
	--- the teacher an honest reason rather than a silently smaller number.
	limitedBy: string?,
}

function Economy.uniquenessFactor(priorCompletions: number): number
	local factor = Economy.UniquenessDecay ^ math.max(priorCompletions, 0)
	return math.max(factor, Economy.UniquenessFloor)
end

function Economy.engagementFactor(actualSeconds: number, expectedSeconds: number): number
	if expectedSeconds <= 0 then
		return Economy.EngagementMin
	end
	local ratio = actualSeconds / expectedSeconds
	if ratio < Economy.EngagementInvalidBelow then
		return 0
	end
	return math.clamp(ratio, Economy.EngagementMin, Economy.EngagementMax)
end

function Economy.qualityFactor(globalPassRate: number): number
	local rate = math.clamp(globalPassRate, 0, 1)
	if rate <= Economy.QualityBandLow then
		local t = rate / Economy.QualityBandLow
		return Economy.QualityFloorTooHard + (1 - Economy.QualityFloorTooHard) * t
	elseif rate <= Economy.QualityBandHigh then
		return 1
	end
	local t = (rate - Economy.QualityBandHigh) / (1 - Economy.QualityBandHigh)
	return 1 - (1 - Economy.QualityFloorTooEasy) * t
end

function Economy.fillRateFactor(members: number, capacity: number): number
	if capacity <= 0 then
		return Economy.FillRateMin
	end
	local fill = math.clamp(members / capacity, 0, 1)
	return Economy.FillRateMin + Economy.FillRateSpan * fill
end

function Economy.ratingFactor(rating: number): number
	local normalised = math.clamp(rating, 0, Economy.MaxRating) / Economy.MaxRating
	return Economy.RatingMin + Economy.RatingSpan * normalised
end

--- Whether this student's completion may contribute to teacher income at all.
--- Note this gates the *teacher's* payout only: the student still earns their own
--- reward, so a new player never sees a degraded game because of an anti-alt rule.
function Economy.countsTowardTeacherPayout(accountAgeDays: number, playSeconds: number): boolean
	return accountAgeDays >= Economy.MinAccountAgeDaysToCount
		and playSeconds >= Economy.MinPlaySecondsToCount
end

function Economy.teacherPayout(input: PayoutInput): PayoutBreakdown
	local uniqueness = Economy.uniquenessFactor(input.priorCompletions)
	local engagement = Economy.engagementFactor(input.actualSeconds, input.expectedSeconds)
	local quality = Economy.qualityFactor(input.globalPassRate)
	local fill = Economy.fillRateFactor(input.classMembers, input.classCapacity)
	local rating = Economy.ratingFactor(input.teacherRating)
	local reach = if input.isTranslatedCompletion then Economy.TranslatedReachShare else 1

	local amount = Economy.BasePayout * uniqueness * engagement * quality * fill * rating * reach
	local limitedBy: string? = nil

	if engagement == 0 then
		amount = 0
		limitedBy = "engagement"
	end

	local remaining = Economy.LifetimePayoutCapPerStudent - input.lifetimePaidByThisStudent
	if remaining <= 0 then
		amount = 0
		limitedBy = "lifetimeCap"
	elseif amount > remaining then
		amount = remaining
		limitedBy = "lifetimeCap"
	end

	return {
		amount = amount,
		uniqueness = uniqueness,
		engagement = engagement,
		quality = quality,
		fill = fill,
		rating = rating,
		reach = reach,
		limitedBy = limitedBy,
	}
end

return Economy
