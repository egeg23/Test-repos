--!strict
--- The squishes: every character in the game, and the rarity ladder they sit on.
---
--- All of them are ours. No licensed character, no meme mascot, no lookalike of
--- one: a squish is a food or a soft thing with a face, drawn in one pastel
--- style, so the whole roster reads as a set.
---
--- Each species is drawn two ways. If Studio has a MeshPart for it under
--- ReplicatedStorage.SquishMeshes (imported from the GLBs in assets/meshes, see
--- the README), that is used. Otherwise Render/SquishModel builds it from
--- primitive parts using `shape` and `palette`, which is what makes the game
--- playable before a single asset has been uploaded.

local Types = require(script.Parent.Parent.Types)

local Squishes = {}

Squishes.RarityOrder = { "common", "rare", "epic", "legendary", "mythic" } :: { Types.Rarity }

export type RarityInfo = {
	rank: number,
	--- Coins per second for a tier-1 squish of this rarity.
	income: number,
	--- What one tier-1 squish is worth in the weekly show.
	showPoints: number,
	colour: { number },
}

Squishes.Rarities = {
	common = { rank = 1, income = 1, showPoints = 1, colour = { 214, 222, 230 } },
	rare = { rank = 2, income = 4, showPoints = 5, colour = { 140, 200, 255 } },
	epic = { rank = 3, income = 15, showPoints = 25, colour = { 200, 150, 255 } },
	legendary = { rank = 4, income = 60, showPoints = 120, colour = { 255, 200, 110 } },
	mythic = { rank = 5, income = 250, showPoints = 600, colour = { 255, 140, 200 } },
} :: { [Types.Rarity]: RarityInfo }

export type Shape =
	"dumpling"
	| "mochi"
	| "toast"
	| "boba"
	| "cloud"
	| "frog"
	| "bao"
	| "pudding"
	| "taiyaki"
	| "macaron"
	| "dragon"
	| "pumpkin"
	| "dango"
	| "sakura"
	| "melon"

export type Season = "autumn" | "winter" | "spring" | "summer"

export type Species = {
	id: string,
	rarity: Types.Rarity,
	shape: Shape,
	--- Body colour then accent colour, as RGB triples. Plain numbers rather than
	--- Color3 so this file loads outside the engine.
	palette: { { number } },
	--- Seasonal squishes never come out of a box. They are the show prize, and
	--- after that they move only by trade.
	season: Season?,
	--- Decal asset id for the icon on cards and the unbox screen. Zero shows the
	--- rarity-coloured placeholder.
	iconId: number,
}

Squishes.List = {
	-- common
	{ id = "dumpling", rarity = "common", shape = "dumpling", palette = { { 255, 240, 222 }, { 255, 196, 170 } }, iconId = 0 },
	{ id = "mochi", rarity = "common", shape = "mochi", palette = { { 255, 214, 226 }, { 255, 255, 255 } }, iconId = 0 },
	{ id = "toast", rarity = "common", shape = "toast", palette = { { 255, 226, 160 }, { 214, 160, 100 } }, iconId = 0 },
	-- rare
	{ id = "boba", rarity = "rare", shape = "boba", palette = { { 226, 206, 246 }, { 90, 64, 70 } }, iconId = 0 },
	{ id = "cloud", rarity = "rare", shape = "cloud", palette = { { 214, 236, 255 }, { 255, 255, 255 } }, iconId = 0 },
	{ id = "frog", rarity = "rare", shape = "frog", palette = { { 196, 240, 206 }, { 255, 248, 230 } }, iconId = 0 },
	-- epic
	{ id = "pandaBao", rarity = "epic", shape = "bao", palette = { { 255, 252, 246 }, { 70, 66, 80 } }, iconId = 0 },
	{ id = "pudding", rarity = "epic", shape = "pudding", palette = { { 255, 224, 140 }, { 170, 110, 70 } }, iconId = 0 },
	-- legendary
	{ id = "rainbowTaiyaki", rarity = "legendary", shape = "taiyaki", palette = { { 255, 200, 230 }, { 180, 230, 255 } }, iconId = 0 },
	{ id = "starMacaron", rarity = "legendary", shape = "macaron", palette = { { 200, 236, 255 }, { 255, 236, 150 } }, iconId = 0 },
	-- mythic
	{ id = "jellyDragon", rarity = "mythic", shape = "dragon", palette = { { 170, 240, 236 }, { 255, 190, 220 } }, iconId = 0 },
	-- seasonal: the weekly show prize
	{ id = "pumpkinPie", rarity = "epic", shape = "pumpkin", palette = { { 255, 196, 130 }, { 150, 200, 120 } }, season = "autumn", iconId = 0 },
	{ id = "snowDango", rarity = "epic", shape = "dango", palette = { { 245, 250, 255 }, { 255, 200, 220 } }, season = "winter", iconId = 0 },
	{ id = "sakuraBun", rarity = "epic", shape = "sakura", palette = { { 255, 220, 236 }, { 255, 170, 200 } }, season = "spring", iconId = 0 },
	{ id = "melonJelly", rarity = "epic", shape = "melon", palette = { { 190, 240, 170 }, { 255, 150, 160 } }, season = "summer", iconId = 0 },
} :: { Species }

local byId: { [string]: Species } = {}
for _, species in Squishes.List do
	assert(byId[species.id] == nil, `duplicate squish species "{species.id}"`)
	assert(Squishes.Rarities[species.rarity] ~= nil, `squish "{species.id}" has unknown rarity`)
	byId[species.id] = species
end

function Squishes.get(id: string): Species?
	return byId[id]
end

function Squishes.rarityRank(rarity: Types.Rarity): number
	return Squishes.Rarities[rarity].rank
end

--- Species a box can produce for a rarity. Seasonal ones are excluded by
--- construction rather than by a flag the box code has to remember to check.
function Squishes.boxPool(rarity: Types.Rarity): { Species }
	local pool: { Species } = {}
	for _, species in Squishes.List do
		if species.rarity == rarity and species.season == nil then
			table.insert(pool, species)
		end
	end
	return pool
end

--- Season from a UTC timestamp, northern-hemisphere months. The show prize
--- follows it, so a player who wins in November gets the autumn squish.
function Squishes.seasonAt(timestamp: number): Season
	local month = tonumber(os.date("!%m", timestamp)) or 1
	if month == 12 or month <= 2 then
		return "winter"
	elseif month <= 5 then
		return "spring"
	elseif month <= 8 then
		return "summer"
	end
	return "autumn"
end

function Squishes.seasonalFor(season: Season): Species?
	for _, species in Squishes.List do
		if species.season == season then
			return species
		end
	end
	return nil
end

return Squishes
