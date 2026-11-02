--!strict
--- The economy, played forward.
---
--- Runs the game's own modules -- the odds and pity, the income formula, the
--- merge rule, the theft rules, the ad and pass numbers -- through simulated
--- players, and fails if the result leaves the bands below. Nothing here is a
--- copy of a game constant: change a number in src/shared/Config and this
--- re-measures the game with it.
---
--- Four questions, each with a pass/fail band:
---
---   1. How long until a free player's first rare, epic, legendary?
---   2. How close does a player who watches ads get to one who bought the pass?
---   3. Does stealing beat playing so badly that it is the only strategy, and
---      can friends farm each other?
---   4. Can a new player lose everything in one evening?
---
--- Run with tools/simulate_economy.sh, which also writes docs/economy.json for
--- the concept page.

local Boxes = require("../src/shared/Config/Boxes")
local Economy = require("../src/shared/Config/Economy")
local Monetization = require("../src/shared/Config/Monetization")
local Squishes = require("../src/shared/Config/Squishes")
local Steal = require("../src/shared/Config/Steal")
local Traps = require("../src/shared/Config/Traps")
local Rng = require("../tests/rng")

local RUNS = tonumber(({...})[1]) or 150
local HOURS = tonumber(({...})[2]) or 20
--- Share of the possible squeeze bonus a real player collects. Nobody taps
--- every squish the moment its cooldown ends; half is a generous average.
local SQUEEZE_EFFORT = 0.5
local ACTIVE_FACTOR = 1 + SQUEEZE_EFFORT * Economy.SqueezeSeconds / Economy.SqueezeCooldown

local failures: { string } = {}
local report: { [string]: any } = {}

local function check(ok: boolean, message: string)
	print(`  {if ok then "ok  " else "FAIL"} {message}`)
	if not ok then
		table.insert(failures, message)
	end
end

local function minutes(seconds: number): string
	if seconds >= 3600 then
		return string.format("%.1f h", seconds / 3600)
	end
	return string.format("%.1f min", seconds / 60)
end

local function percentile(values: { number }, p: number): number
	local sorted = table.clone(values)
	table.sort(sorted)
	local index = math.clamp(math.ceil(p * #sorted), 1, #sorted)
	return sorted[index]
end

local function heading(text: string)
	print(`\n{string.rep("=", 74)}\n{text}\n{string.rep("=", 74)}`)
end

-- ---------------------------------------------------------------------------
-- A simulated player
-- ---------------------------------------------------------------------------

type Owned = { species: string, tier: number, rarity: string, uid: number }

type Player = {
	coins: number,
	owned: { Owned },
	boughtSlots: number,
	pity: { [string]: number },
	first: { [string]: number },
	clock: number,
	nextUid: number,
	pass: boolean,
	boxesOpened: number,
}

local function newPlayer(pass: boolean): Player
	local player: Player = {
		coins = Economy.StartCoins,
		owned = {},
		boughtSlots = 0,
		pity = {},
		first = {},
		clock = 0,
		nextUid = 1,
		pass = pass,
		boxesOpened = 0,
	}
	local starter = Squishes.get(Economy.StarterSpecies)
	assert(starter ~= nil)
	table.insert(player.owned, { species = starter.id, tier = 1, rarity = starter.rarity, uid = 0 })
	return player
end

local function income(owned: Owned): number
	return Economy.incomePerSecond(owned.rarity :: any, owned.tier)
end

local function capacity(player: Player): number
	return Economy.totalSlots(player.boughtSlots, false)
end

--- Sorts best-first; the top `capacity` are on shelves.
local function arrange(player: Player)
	table.sort(player.owned, function(a, b)
		return income(a) > income(b)
	end)
end

local function shelvedIncome(player: Player): number
	arrange(player)
	local total = 0
	for index = 1, math.min(#player.owned, capacity(player)) do
		total += income(player.owned[index])
	end
	return total
end

local function mergeAll(player: Player)
	local merged = true
	while merged do
		merged = false
		local seen: { [string]: number } = {}
		for index, owned in player.owned do
			local key = `{owned.species}:{owned.tier}`
			local other = seen[key]
			if other ~= nil and owned.tier < Economy.MaxTier then
				local keep = player.owned[other]
				keep.tier += 1
				table.remove(player.owned, index)
				merged = true
				break
			end
			seen[key] = index
		end
	end
end

--- Keeps the collection to shelves plus a small pocket of merge candidates,
--- selling the least valuable.
local function trim(player: Player)
	arrange(player)
	local keep = capacity(player) + 6
	while #player.owned > keep do
		local worst = table.remove(player.owned) :: Owned
		player.coins += math.floor(income(worst) * Economy.ResaleSeconds)
	end
end

local function multiplier(player: Player, adBoost: boolean): number
	return Economy.incomeMultiplier({ incomePass = player.pass, adBoost = adBoost, paidBoost = false })
end

local function earn(player: Player, seconds: number, adBoost: boolean)
	player.coins += shelvedIncome(player) * multiplier(player, adBoost) * ACTIVE_FACTOR * seconds
	player.clock += seconds
end

local function openBox(player: Player, box: Boxes.Box, rng: () -> number)
	local rarity, counter = Boxes.rollRarity(box, player.pity[box.id] or 0, rng)
	player.pity[box.id] = counter
	local species = Boxes.rollSpecies(rarity, rng)
	player.boxesOpened += 1
	if player.first[rarity] == nil then
		player.first[rarity] = player.clock
	end
	table.insert(player.owned, { species = species.id, tier = 1, rarity = rarity, uid = player.nextUid })
	player.nextUid += 1
	mergeAll(player)
	trim(player)
end

local coinBoxes: { Boxes.Box } = {}
for _, box in Boxes.List do
	if box.coins ~= nil then
		table.insert(coinBoxes, box)
	end
end
table.sort(coinBoxes, function(a, b)
	return (a.coins :: number) < (b.coins :: number)
end)

--- What a sensible free player buys next: a shelf when the shelves are full
--- and it is cheap relative to income, otherwise the best box that ten minutes
--- of income can pay for.
local function nextPurchase(player: Player): (string, number, Boxes.Box?)
	local rate = math.max(shelvedIncome(player) * multiplier(player, false) * ACTIVE_FACTOR, 0.01)
	local slotCost = Economy.nextSlotCost(player.boughtSlots)
	if slotCost ~= nil and #player.owned >= capacity(player) and slotCost <= rate * 300 then
		return "slot", slotCost, nil
	end
	local choice = coinBoxes[1]
	for _, box in coinBoxes do
		if (box.coins :: number) <= math.max(player.coins, rate * 600) then
			choice = box
		end
	end
	return "box", choice.coins :: number, choice
end

--- Plays a player forward until `untilSeconds`.
local function play(player: Player, untilSeconds: number, rng: () -> number)
	while player.clock < untilSeconds do
		local kind, cost, box = nextPurchase(player)
		if player.coins < cost then
			local rate = shelvedIncome(player) * multiplier(player, false) * ACTIVE_FACTOR
			local wait = math.max(1, math.ceil((cost - player.coins) / math.max(rate, 0.01)))
			wait = math.min(wait, untilSeconds - player.clock)
			earn(player, wait, false)
			if player.coins < cost then
				continue
			end
		end
		player.coins -= cost
		if kind == "slot" then
			player.boughtSlots += 1
		elseif box ~= nil then
			openBox(player, box, rng)
		end
	end
end

-- ---------------------------------------------------------------------------
-- 1. Time to the first of each rarity
-- ---------------------------------------------------------------------------

heading("1. Time to first squish of each rarity (free player, no ads, no pass)")

local firsts: { [string]: { number } } = {}
local incomeAt: { [number]: { number } } = { [1] = {}, [3] = {}, [10] = {} }
for run = 1, RUNS do
	local rng = Rng.new(1000 + run)
	local player = newPlayer(false)
	for _, checkpoint in { 1, 3, 10 } do
		play(player, checkpoint * 3600, rng)
		table.insert(incomeAt[checkpoint], shelvedIncome(player))
	end
	play(player, HOURS * 3600, rng)
	for _, rarity in Squishes.RarityOrder do
		local list = firsts[rarity]
		if list == nil then
			list = {}
			firsts[rarity] = list
		end
		-- Never reaching it inside the horizon counts as the horizon, which
		-- understates the time: the band below is still a fair test of "too slow".
		table.insert(list, player.first[rarity] or HOURS * 3600)
	end
end

print(string.format("  %-10s %10s %10s", "rarity", "median", "p90"))
report.firsts = {}
for _, rarity in Squishes.RarityOrder do
	local list = firsts[rarity]
	local median, p90 = percentile(list, 0.5), percentile(list, 0.9)
	print(string.format("  %-10s %10s %10s", rarity, minutes(median), minutes(p90)))
	report.firsts[rarity] = { median = median, p90 = p90 }
end
report.incomePerSecond = {}
for _, checkpoint in { 1, 3, 10 } do
	local median = percentile(incomeAt[checkpoint], 0.5)
	print(string.format("  income after %2d h: %8.0f coins/sec (median)", checkpoint, median))
	report.incomePerSecond[tostring(checkpoint)] = median
end

print("")
check(report.firsts.rare.median <= 5 * 60, "first rare inside the first 5 minutes (median)")
check(report.firsts.epic.median <= 30 * 60, "first epic inside the first half hour (median)")
check(report.firsts.epic.p90 <= 60 * 60, "nine players in ten have an epic within the hour")
check(
	report.firsts.legendary.median >= 60 * 60 and report.firsts.legendary.median <= 6 * 3600,
	"first legendary between 1 and 6 hours (median): a goal, not a gift"
)
check(report.firsts.mythic.median >= 8 * 3600, "mythic stays rare: median beyond 8 hours")

-- ---------------------------------------------------------------------------
-- 2. Ads against the pass
-- ---------------------------------------------------------------------------

heading("2. Catching a paying player by watching ads")

local adBoost = Monetization.getAdReward("adIncomeBoost")
local adGift = Monetization.getAdReward("adCoinGift")
local pass = Monetization.getPass("doubleCoins")
assert(adBoost ~= nil and adGift ~= nil and pass ~= nil)

--- Share of a session the ad boost can cover, and how many ads that takes,
--- honouring both the cooldown and the daily limit.
local function adPlan(sessionSeconds: number): (number, number, number)
	local boostSeconds = adBoost.boostSeconds :: number
	local boosted, ads, gifts = 0, 0, 0
	local t = 0
	while t < sessionSeconds and ads < adBoost.dailyLimit do
		boosted += math.min(boostSeconds, sessionSeconds - t)
		ads += 1
		t += math.max(adBoost.cooldownSeconds, boostSeconds)
	end
	local g = 0
	while g < sessionSeconds and gifts < adGift.dailyLimit do
		gifts += 1
		g += adGift.cooldownSeconds
	end
	return boosted / sessionSeconds, ads, gifts
end

local SESSION = 60 * 60
local uptime, boostAds, giftAds = adPlan(SESSION)
local giftShare = giftAds * (adGift.incomeSeconds :: number) / SESSION
local free = 1
local adWatcher = 1 + uptime * Economy.AdBoostIncomeBonus + giftShare
local payer = 1 + Economy.PassIncomeBonus
local catchUp = (adWatcher - free) / (payer - free)
local adsPerHour = boostAds + giftAds

print(string.format("  one-hour session, income relative to a free player"))
print(string.format("    free, no ads            x%.2f", free))
print(string.format("    free, watches ads       x%.2f   (%d ads: %d boost, %d gift; boost covers %d%%)", adWatcher, adsPerHour, boostAds, giftAds, math.floor(uptime * 100 + 0.5)))
print(string.format("    bought %s (%d R$)  x%.2f", pass.id, pass.robux, payer))
print(string.format("  ads close %d%% of the gap to the pass", math.floor(catchUp * 100 + 0.5)))

local _, dayAds = adPlan(24 * 3600)
local dailyRobux = dayAds * adBoost.robuxEquivalent
print(string.format("  the boost ad's daily limit (%d) is worth about %d Robux of boosts a day", dayAds, dailyRobux))

report.catchUp = {
	free = free,
	adWatcher = adWatcher,
	payer = payer,
	share = catchUp,
	adsPerHour = adsPerHour,
	passRobux = pass.robux,
}

print("")
check(catchUp >= 0.5 and catchUp <= 0.85, "ads close most of the gap (50-85%) without erasing it")
check(adsPerHour <= 6, "catching up takes at most six ads an hour")

-- The rainbow box against coin boxes: how much free play it is worth.
local function expectedIncome(box: Boxes.Box): number
	local value = 0
	for _, rarity in Squishes.RarityOrder do
		value += Boxes.oddsPercent(box, rarity) / 100 * Economy.incomePerSecond(rarity, 1)
	end
	return value
end
local rainbow = Boxes.get("rainbow")
local star = Boxes.get("star")
assert(rainbow ~= nil and star ~= nil)
local rainbowIncome = expectedIncome(rainbow)
local starIncome = expectedIncome(star)
local starEquivalent = rainbowIncome / starIncome
local threeHourRate = report.incomePerSecond["3"] * ACTIVE_FACTOR
local playMinutes = starEquivalent * (star.coins :: number) / threeHourRate / 60
print(string.format("  a rainbow box (49 R$) is worth %.2f star boxes, or about %.0f minutes of play at 3 h", starEquivalent, playMinutes))
report.rainbow = { starBoxes = starEquivalent, playMinutesAt3h = playMinutes }
check(starEquivalent <= 2, "a paid box is worth at most two of the best coin box")

-- ---------------------------------------------------------------------------
-- 3. Stealing
-- ---------------------------------------------------------------------------

heading("3. Stealing as a strategy")

-- The thief's odds on one attempt, from the real rules. The carry distance is
-- the median plot-to-plot carry; the defender is assumed to be at the base
-- half of the time and to land the pillow on a third of those.
local trampoline = Traps.get("trampoline")
local cannon = Traps.get("cannon")
assert(trampoline ~= nil and cannon ~= nil)
local CARRY_STUDS = 190
local DEFENDER_SAVE = 0.5 * (1 / 3)

local function attemptSuccess(tier: number, trapLevel: number): number
	local seconds = CARRY_STUDS / Steal.carrySpeed(tier)
	local hold = Steal.holdProbability(tier, seconds)
	local cannonMiss = 1
	local bounce = 0
	if trapLevel > 0 then
		cannonMiss = 1 - ((cannon.levels[trapLevel].chance :: number))
		bounce = trampoline.levels[trapLevel].chance :: number
	end
	-- A trampoline bounce throws the thief back into the base, which gives the
	-- defender a second chance rather than ending the attempt.
	local defender = DEFENDER_SAVE * (1 + bounce)
	return hold * cannonMiss * (1 - math.min(defender, 0.9)) * (1 - Steal.ReturnHomeChance)
end

-- A victim pool of players at three hours, from the same simulation.
local victims: { Player } = {}
for run = 1, 50 do
	local victim = newPlayer(false)
	play(victim, 3 * 3600, Rng.new(5000 + run))
	arrange(victim)
	table.insert(victims, victim)
end

--- Attempt length: walk over, hold, carry back.
local function attemptSeconds(tier: number): number
	return CARRY_STUDS / Steal.NormalWalkSpeed + Steal.holdSeconds(tier) + CARRY_STUDS / Steal.carrySpeed(tier)
end

-- One hour of a thief on a full server: five other bases, each closed by its
-- shield after a loss and by its daily cap. The thief always goes for the
-- best squish that is not the last one.
local OTHERS = 5
local thiefGain, thiefSuccesses = 0, 0
local honestGain = 0
for index, victim in victims do
	local rng = Rng.new(9000 + index)
	local trapLevel = 1
	local clock = 0
	local openAt: { number } = table.create(OTHERS, 0)
	local losses: { number } = table.create(OTHERS, 0)
	while clock < 3600 do
		local target = 0
		for other = 1, OTHERS do
			if openAt[other] <= clock and losses[other] < Steal.DailyLossCap then
				target = other
				break
			end
		end
		if target == 0 then
			clock += 30
			continue
		end
		-- The first ProtectedFavourites are the victim's favourites and cannot
		-- be stolen; the thief takes the best of the rest. The five bases are
		-- modelled on the same three-hour player, offset so they differ.
		local stolen = victim.owned[math.min(Steal.ProtectedFavourites + target, #victim.owned)]
		if stolen == nil or #victim.owned <= Steal.ProtectedFavourites then
			break
		end
		clock += attemptSeconds(stolen.tier)
		if rng() < attemptSuccess(stolen.tier, trapLevel) then
			thiefGain += income(stolen)
			thiefSuccesses += 1
			losses[target] += 1
			openAt[target] = clock + Steal.ShieldAfterTheftSeconds
			clock += Steal.ThiefCooldownSeconds
		end
	end
	-- The same hour spent honestly, from the same starting point.
	local honest = newPlayer(false)
	play(honest, 3 * 3600, Rng.new(5000 + index))
	local before = shelvedIncome(honest)
	play(honest, 4 * 3600, Rng.new(7000 + index))
	honestGain += shelvedIncome(honest) - before
end
thiefGain /= #victims
honestGain /= #victims
thiefSuccesses /= #victims
local ratio = thiefGain / math.max(honestGain, 1e-9)
print(string.format("  an hour of stealing at 3 h: %.1f successful thefts, +%.0f coins/sec", thiefSuccesses, thiefGain))
print(string.format("  an hour of honest play at 3 h: +%.0f coins/sec", honestGain))
print(string.format("  stealing earns %.2fx what playing does", ratio))
print(string.format("  chance one attempt lands, tier 1 vs no traps: %d%%; vs level-3 traps: %d%%", math.floor(attemptSuccess(1, 0) * 100 + 0.5), math.floor(attemptSuccess(1, 3) * 100 + 0.5)))
report.steal = {
	thiefGain = thiefGain,
	honestGain = honestGain,
	ratio = ratio,
	successesPerHour = thiefSuccesses,
	attemptNoTraps = attemptSuccess(1, 0),
	attemptMaxTraps = attemptSuccess(1, 3),
}
check(ratio >= 0.3, "stealing is worth trying (at least 0.3x honest play)")
check(ratio <= 3, "stealing does not dwarf playing (at most 3x)")

-- A ring: two friends stealing one squish back and forth. Theft mints no
-- coins -- no line of StealService adds any -- so all a ring can do is move a
-- squish between two shelves. While one of them carries, neither squeezes, and
-- one move in five the squish runs home anyway. Their combined income can
-- only fall.
local ringMoves = 3600 / (Steal.ShieldAfterTheftSeconds + attemptSeconds(1))
local carryingShare = ringMoves * attemptSeconds(1) / 3600
local ringShare = (1 + (ACTIVE_FACTOR - 1) * (1 - carryingShare)) / ACTIVE_FACTOR
print(string.format("  a two-friend ring moves a squish %.1f times an hour; their combined income is %d%% of just playing", ringMoves, math.floor(ringShare * 100 + 0.5)))
report.ring = { movesPerHour = ringMoves, incomeShare = ringShare }
check(ringShare <= 1, "a theft ring earns no more than playing")

-- ---------------------------------------------------------------------------
-- 4. A new player's first evening
-- ---------------------------------------------------------------------------

heading("4. A new player's first evening, against relentless thieves")

-- Worst case: thieves never fail, always take the best squish the rules
-- allow, and try again the moment the shield drops.
local EVENING = 3 * 3600
local robbedIncomes: { number } = {}
local untouchedIncomes: { number } = {}
local lossesList: { number } = {}
for run = 1, RUNS do
	local seed = 20000 + run
	local untouched = newPlayer(false)
	play(untouched, EVENING, Rng.new(seed))
	local untouchedIncome = shelvedIncome(untouched)

	local robbed = newPlayer(false)
	local rng = Rng.new(seed)
	local shieldUntil = 0
	local losses = 0
	local step = 60
	while robbed.clock < EVENING do
		play(robbed, robbed.clock + step, rng)
		local shelved = math.min(#robbed.owned, capacity(robbed))
		local allowed = Steal.canBeRobbed({
			playSeconds = robbed.clock,
			forfeitedProtection = false,
			shelved = shelved,
			shieldUntil = shieldUntil,
			lossesToday = losses,
			online = true,
		}, robbed.clock)
		if allowed and #robbed.owned > Steal.ProtectedFavourites then
			-- The favourites cannot be taken; the thief takes the best of the rest.
			arrange(robbed)
			table.remove(robbed.owned, Steal.ProtectedFavourites + 1)
			losses += 1
			shieldUntil = robbed.clock + Steal.ShieldAfterTheftSeconds
		end
	end
	table.insert(robbedIncomes, shelvedIncome(robbed))
	table.insert(untouchedIncomes, untouchedIncome)
	table.insert(lossesList, losses)
end
-- Robbed and untouched players draw different boxes once their histories
-- diverge, so a single pair says little. The comparison is between the two
-- populations: the median robbed player against the median untouched one, and
-- the unlucky tenth against the unlucky tenth.
local keptMedian = percentile(robbedIncomes, 0.5) / math.max(percentile(untouchedIncomes, 0.5), 1e-9)
local keptWorst = percentile(robbedIncomes, 0.1) / math.max(percentile(untouchedIncomes, 0.1), 1e-9)
local maxLosses = percentile(lossesList, 1)
print(string.format("  squishes lost in the evening: at most %d (daily cap %d)", maxLosses, Steal.DailyLossCap))
print(string.format("  income kept vs an untouched player: median %d%%, worst tenth %d%%", math.floor(keptMedian * 100 + 0.5), math.floor(keptWorst * 100 + 0.5)))
report.newbie = { keptMedian = keptMedian, keptWorst = keptWorst, maxLosses = maxLosses }
check(maxLosses <= Steal.DailyLossCap, "losses never pass the daily cap")
check(keptMedian >= 0.5, "a typical new player keeps at least half their income")
check(keptWorst >= 0.3, "even the unluckiest tenth keep at least 30%")

-- ---------------------------------------------------------------------------

print("\nREPORT")
local function encode(value: any, indent: string): string
	if typeof(value) == "table" then
		local keys = {}
		for key in value do
			table.insert(keys, tostring(key))
		end
		table.sort(keys)
		local parts = {}
		for _, key in keys do
			table.insert(parts, `{indent}  "{key}": {encode(value[key], indent .. "  ")}`)
		end
		return "{\n" .. table.concat(parts, ",\n") .. `\n{indent}}`
	elseif typeof(value) == "number" then
		return string.format("%.4f", value)
	end
	return `"{tostring(value)}"`
end
print(encode(report, ""))

if #failures > 0 then
	print(`\n{#failures} band(s) failed:`)
	for _, failure in failures do
		print(`  - {failure}`)
	end
	error("economy simulation failed", 0)
end
print("\nEconomy simulation: every band holds.")
