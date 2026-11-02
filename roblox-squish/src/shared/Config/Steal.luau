--!strict
--- Theft: who may be robbed, how carrying feels, and what limits the damage.
---
--- Stealing is the genre's heart and also the fastest way to make a child cry
--- and quit. The rules here are what keep it a game:
---
---   * a new player cannot be robbed for their first minutes of play;
---   * nobody can lose their last squish on a shelf, and nobody can lose their
---     favourites -- the three most valuable squishes on their shelves are never
---     for taking, so the ones a child is proudest of are always safe;
---   * after a theft the victim's base is shielded for a while;
---   * nobody loses more than a handful of squishes per day;
---   * a stolen squish is slippery, heavy and homesick: it can bounce out of the
---     thief's arms, it slows them, and on arrival it may run back home.
---
--- Theft creates no coins. It only moves a squish, and the return-home roll
--- means a ring of friends robbing each other ends up with less than it started
--- with. tools/simulate_economy checks both.

local Steal = {}

--- Seconds of play before a player can be robbed.
Steal.NewbieProtectionSeconds = 15 * 60
--- A base must keep at least this many squishes on shelves after a theft.
Steal.MinShelvedAfterTheft = 1
--- Shield after being robbed.
Steal.ShieldAfterTheftSeconds = 6 * 60
--- Most squishes one player can lose to theft in a UTC day. Past this their
--- base stays closed to thieves until midnight.
Steal.DailyLossCap = 5

--- Movement. Roblox's default walk speed is 16.
Steal.NormalWalkSpeed = 16
Steal.CarryWalkSpeed = 12
Steal.CarrySpeedPerTier = 1
Steal.MinCarryWalkSpeed = 8

--- Holding the prompt. Bigger squishes take longer to pick up.
Steal.HoldSeconds = 1.5
Steal.HoldSecondsPerTier = 0.5

--- Chance per second of carrying that the squish springs loose. Rises with tier:
--- a big squish is harder to hold.
Steal.SlipChancePerSecond = 0.025
Steal.SlipChancePerTier = 0.008
--- A loose squish bounces, and goes home on its own after this long.
Steal.LooseReturnSeconds = 6
--- Carrying longer than this means the squish wriggles free and goes home.
Steal.CarryTimeoutSeconds = 45

--- On delivery the squish may run back home anyway.
Steal.ReturnHomeChance = 0.3

--- After a successful theft the thief's hands are sticky for a while and they
--- cannot pick up another squish. Without it one fast thief empties a server.
Steal.ThiefCooldownSeconds = 5 * 60

--- The defender's pillow.
Steal.PillowRange = 9
Steal.PillowCooldown = 1.2
Steal.PillowKnockback = 70

--- Server tolerance on the prompt: the thief's root must be within this many
--- studs of the shelf when the steal completes.
Steal.PromptDistance = 8
Steal.DistanceSlack = 3

export type VictimState = {
	playSeconds: number,
	forfeitedProtection: boolean,
	shelved: number,
	shieldUntil: number,
	lossesToday: number,
	online: boolean,
}

--- Whether a base can be robbed right now. The reason is a string key the
--- interface turns into a sentence, so the thief always knows why not.
function Steal.canBeRobbed(victim: VictimState, now: number): (boolean, string?)
	if not victim.online then
		return false, "offline"
	end
	if victim.playSeconds < Steal.NewbieProtectionSeconds and not victim.forfeitedProtection then
		return false, "newbie"
	end
	if now < victim.shieldUntil then
		return false, "shield"
	end
	if victim.lossesToday >= Steal.DailyLossCap then
		return false, "dailyCap"
	end
	if victim.shelved <= Steal.ProtectedFavourites or victim.shelved - 1 < Steal.MinShelvedAfterTheft then
		return false, "lastSquish"
	end
	return true, nil
end

export type ShelfEntry = { uid: string, income: number }

--- How many of a base's most valuable squishes can never be stolen.
Steal.ProtectedFavourites = 3

--- The favourites: the shelf's most valuable squishes, never stealable. Ties go
--- to the lower uid so every server picks the same ones.
function Steal.favourites(entries: { ShelfEntry }): { [string]: boolean }
	local sorted = table.clone(entries)
	table.sort(sorted, function(a, b)
		if a.income ~= b.income then
			return a.income > b.income
		end
		return a.uid < b.uid
	end)
	local result: { [string]: boolean } = {}
	for index = 1, math.min(Steal.ProtectedFavourites, #sorted) do
		result[sorted[index].uid] = true
	end
	return result
end

function Steal.carrySpeed(tier: number): number
	return math.max(Steal.MinCarryWalkSpeed, Steal.CarryWalkSpeed - Steal.CarrySpeedPerTier * (tier - 1))
end

function Steal.holdSeconds(tier: number): number
	return Steal.HoldSeconds + Steal.HoldSecondsPerTier * (tier - 1)
end

function Steal.slipChancePerSecond(tier: number): number
	return Steal.SlipChancePerSecond + Steal.SlipChancePerTier * (tier - 1)
end

--- Probability of carrying a squish of `tier` for `seconds` without it slipping.
function Steal.holdProbability(tier: number, seconds: number): number
	return (1 - Steal.slipChancePerSecond(tier)) ^ seconds
end

return Steal
