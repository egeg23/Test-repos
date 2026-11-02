--!strict
--- Squish traps at the entrance of a base.
---
--- Every trap reacts only to a player carrying one of the owner's squishes out.
--- A friend walking in empty-handed is never bounced, slimed or shot at: traps
--- defend, they do not grief, and that is also why they need no off switch.
---
--- Three slots in the entrance path, one trap type each. Levels make a trap
--- stronger; level 0 means not built.

local Traps = {}

export type Level = {
	cost: number,
	--- Trampoline: chance the carrier is thrown back into the base.
	--- Slime: walk speed multiplier while in it, and how long it lingers.
	--- Cannon: chance per shot to knock the squish loose, and shot cooldown.
	chance: number?,
	slowFactor: number?,
	slowSeconds: number?,
	cooldown: number?,
}

export type Trap = {
	id: string,
	--- Which entrance slot it occupies, from the door outward.
	slot: number,
	levels: { Level },
	colour: { number },
}

Traps.List = {
	{
		id = "trampoline",
		slot = 1,
		levels = {
			{ cost = 400, chance = 0.25 },
			{ cost = 3000, chance = 0.35 },
			{ cost = 20000, chance = 0.45 },
		},
		colour = { 255, 170, 200 },
	},
	{
		id = "slime",
		slot = 2,
		levels = {
			{ cost = 800, slowFactor = 0.6, slowSeconds = 2 },
			{ cost = 6000, slowFactor = 0.5, slowSeconds = 3 },
			{ cost = 40000, slowFactor = 0.4, slowSeconds = 4 },
		},
		colour = { 170, 240, 190 },
	},
	{
		id = "cannon",
		slot = 3,
		levels = {
			{ cost = 1500, chance = 0.2, cooldown = 4 },
			{ cost = 12000, chance = 0.3, cooldown = 3 },
			{ cost = 80000, chance = 0.4, cooldown = 2.5 },
		},
		colour = { 190, 210, 255 },
	},
} :: { Trap }

Traps.MaxLevel = 3

--- Trampoline throw: upward and back toward the base, studs per second.
Traps.TrampolineUp = 55
Traps.TrampolineBack = 45

local byId: { [string]: Trap } = {}
local slotsTaken: { [number]: boolean } = {}
for _, trap in Traps.List do
	assert(byId[trap.id] == nil, `duplicate trap "{trap.id}"`)
	assert(not slotsTaken[trap.slot], `two traps share entrance slot {trap.slot}`)
	assert(#trap.levels == Traps.MaxLevel, `trap "{trap.id}" must have {Traps.MaxLevel} levels`)
	slotsTaken[trap.slot] = true
	byId[trap.id] = trap
end

function Traps.get(id: string): Trap?
	return byId[id]
end

function Traps.level(trap: Trap, level: number): Level?
	if level < 1 then
		return nil
	end
	return trap.levels[level]
end

--- Cost of the next level, or nil at max.
function Traps.nextCost(trap: Trap, level: number): number?
	local nextLevel = trap.levels[level + 1]
	if nextLevel == nil then
		return nil
	end
	return nextLevel.cost
end

return Traps
