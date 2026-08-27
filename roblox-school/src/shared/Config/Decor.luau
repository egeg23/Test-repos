--!strict
--- What each room looks like.
---
--- The school is built from parts at run time, so "the maths room is blue and
--- has a chalk haze" has to live somewhere as data. It lives here, next to the
--- subject list it is keyed by, rather than inside the builder -- a builder that
--- also holds the palette becomes a thousand-line file where changing a colour
--- means reading geometry.
---
--- Two rules the effects obey, because they are cheap to state and expensive to
--- rediscover on a full server:
---
---   * Every emitter is capped. `Rate` times `Lifetime` is the particle count a
---     room carries forever, and thirty rooms of unbounded haze is how a phone
---     drops to eight frames. `Decor.particleBudget` enforces it.
---   * Nothing here is gameplay. A room's light and haze say which subject you
---     walked into; they never say whether you passed. Anything a player could
---     mistake for feedback belongs in the lesson UI, not the walls.

local Decor = {}

export type Effect = "chalk" | "sparks" | "steam" | "paint" | "dust" | "leaves" | "none"

--- Colours are packed 0xRRGGBB integers and materials are plain strings, not
--- Color3 and Enum.Material. That is not a style choice: this file is config, and
--- config in this project imports nothing from the Roblox engine so the unit
--- tests can execute it directly under standalone Luau. Build converts both at
--- the point a part is created, once, in one place.
export type Theme = {
	--- Walls, and the trim that runs under the ceiling.
	wall: number,
	trim: number,
	--- The board at the front. Slate for most, whiteboard for the lab.
	board: number,
	--- Floor material and colour. Wood for the humanities, rubber for the gym.
	floor: number,
	floorMaterial: string,
	--- Tint and reach of the ceiling light. Warm rooms feel older.
	light: number,
	lightBrightness: number,
	--- The ambient effect, and its colour.
	effect: Effect,
	effectColour: number,
	--- Props the builder scatters: what they are is up to the builder, how many
	--- is up to the room.
	props: number,
}

local function theme(t: Theme): Theme
	return t
end

--- Maths and logic are cold and bright; the humanities are warm and wooden; the
--- lab is clinical; art is the only room that is louder than its occupants.
Decor.Subjects = {
	math = theme({
		wall = 0xE2E8F2,
		trim = 0x4660BE,
		board = 0x26342C,
		floor = 0xC4CAD4,
		floorMaterial = "Concrete",
		light = 0xDCE8FF,
		lightBrightness = 1.6,
		effect = "chalk",
		effectColour = 0xECF0F8,
		props = 4,
	}),
	science = theme({
		wall = 0xE4EEEA,
		trim = 0x3A9682,
		board = 0xF0F4F6,
		floor = 0xB4C4C0,
		floorMaterial = "Pebble",
		light = 0xE2F6F0,
		lightBrightness = 1.8,
		effect = "steam",
		effectColour = 0xBEE8DE,
		props = 6,
	}),
	logic = theme({
		wall = 0xDEE0EA,
		trim = 0x7868BE,
		board = 0x222230,
		floor = 0xBABCC8,
		floorMaterial = "Concrete",
		light = 0xD6D0F6,
		lightBrightness = 1.5,
		effect = "sparks",
		effectColour = 0xAA96FF,
		props = 4,
	}),
	pe = theme({
		wall = 0xEEE8D6,
		trim = 0xD66C3C,
		board = 0x343E3A,
		floor = 0xB2764E,
		floorMaterial = "WoodPlanks",
		light = 0xFFF4DC,
		lightBrightness = 2.2,
		effect = "dust",
		effectColour = 0xE2D0AC,
		props = 5,
	}),
	art = theme({
		wall = 0xF6EEE8,
		trim = 0xD25278,
		board = 0xFAF8F4,
		floor = 0xCEBCAC,
		floorMaterial = "Fabric",
		light = 0xFFECE8,
		lightBrightness = 1.9,
		effect = "paint",
		effectColour = 0xEC82A0,
		props = 7,
	}),
	literature = theme({
		wall = 0xECE2D0,
		trim = 0x966A3E,
		board = 0x2C342A,
		floor = 0x8C6442,
		floorMaterial = "WoodPlanks",
		light = 0xFFE8C6,
		lightBrightness = 1.4,
		effect = "dust",
		effectColour = 0xE8D6B2,
		props = 6,
	}),
	history = theme({
		wall = 0xE4D8C6,
		trim = 0x7E6046,
		board = 0x2E2C26,
		floor = 0x7C5C3E,
		floorMaterial = "WoodPlanks",
		light = 0xFFE2BA,
		lightBrightness = 1.3,
		effect = "dust",
		effectColour = 0xE0CAA4,
		props = 6,
	}),
	language = theme({
		wall = 0xE8E4D8,
		trim = 0x588C6C,
		board = 0x28382E,
		floor = 0x987450,
		floorMaterial = "WoodPlanks",
		light = 0xF8F0D8,
		lightBrightness = 1.5,
		effect = "leaves",
		effectColour = 0x8CBE96,
		props = 5,
	}),
} :: { [string]: Theme }

--- The rooms that are not a subject. They are keyed the same way so the builder
--- takes one code path, and they are listed apart because they are laid out by
--- hand rather than by walking the subject list.
Decor.Halls = {
	gym = theme({
		wall = 0xEEEAE0,
		trim = 0xD66C3C,
		board = 0x343E3A,
		floor = 0xBA7C52,
		floorMaterial = "WoodPlanks",
		light = 0xFFF8E8,
		lightBrightness = 2.4,
		effect = "dust",
		effectColour = 0xE4D4B2,
		props = 8,
	}),
	library = theme({
		wall = 0xE2D4BE,
		trim = 0x785838,
		board = 0x342C22,
		floor = 0x705238,
		floorMaterial = "WoodPlanks",
		light = 0xFFDEB0,
		lightBrightness = 1.1,
		effect = "dust",
		effectColour = 0xECD8B0,
		props = 10,
	}),
	assembly = theme({
		wall = 0xD4CCD6,
		trim = 0x963C46,
		board = 0x461820,
		floor = 0x602830,
		floorMaterial = "Fabric",
		light = 0xFFE2D6,
		lightBrightness = 1.7,
		effect = "none",
		effectColour = 0xFFFFFF,
		props = 0,
	}),
	staffroom = theme({
		wall = 0xE0E2E8,
		trim = 0x4660BE,
		board = 0x262C38,
		floor = 0x9698A2,
		floorMaterial = "Carpet",
		light = 0xEEF0FC,
		lightBrightness = 1.5,
		effect = "none",
		effectColour = 0xFFFFFF,
		props = 5,
	}),
} :: { [string]: Theme }

--- A room with no theme still has to be buildable, or adding a subject to the
--- config crashes the world instead of producing a plain room.
Decor.Default = theme({
	wall = 0xE8E4DC,
	trim = 0x787C88,
	board = 0x2C4236,
	floor = 0xCEC8BC,
	floorMaterial = "SmoothPlastic",
	light = 0xFFFFFF,
	lightBrightness = 1.5,
	effect = "none",
	effectColour = 0xFFFFFF,
	props = 3,
})

function Decor.forSubject(id: string): Theme
	return Decor.Subjects[id] or Decor.Default
end

function Decor.forHall(id: string): Theme
	return Decor.Halls[id] or Decor.Default
end

--- Emitter settings per effect, and the cap that keeps them honest.
export type Emission = {
	rate: number,
	lifetime: number,
	speed: number,
	size: number,
	transparency: number,
	--- Upward drift. Chalk falls, steam rises, sparks go nowhere.
	drift: number,
	spread: number,
}

Decor.Emissions = {
	chalk = { rate = 3, lifetime = 5, speed = 0.6, size = 0.28, transparency = 0.72, drift = -1.4, spread = 14 },
	sparks = { rate = 5, lifetime = 1.2, speed = 5, size = 0.16, transparency = 0.25, drift = 0, spread = 40 },
	steam = { rate = 4, lifetime = 3.5, speed = 1.4, size = 0.9, transparency = 0.86, drift = 2.2, spread = 10 },
	paint = { rate = 6, lifetime = 2.6, speed = 2.4, size = 0.34, transparency = 0.4, drift = -0.6, spread = 55 },
	dust = { rate = 2, lifetime = 9, speed = 0.3, size = 0.2, transparency = 0.8, drift = 0.15, spread = 22 },
	leaves = { rate = 1.5, lifetime = 7, speed = 1, size = 0.5, transparency = 0.35, drift = -0.9, spread = 30 },
} :: { [string]: Emission }

--- No emitter may hold more than this many live particles. Rate times lifetime
--- is that number, and it is checked rather than trusted: the tuning pass that
--- makes a room look right is exactly the pass that forgets the frame budget.
Decor.MaxLiveParticles = 48

function Decor.particleBudget(effect: Effect): number
	local emission = Decor.Emissions[effect]
	if emission == nil then
		return 0
	end
	return emission.rate * emission.lifetime
end

for name, emission in Decor.Emissions do
	assert(
		emission.rate * emission.lifetime <= Decor.MaxLiveParticles,
		`effect "{name}" holds {emission.rate * emission.lifetime} particles, over the {Decor.MaxLiveParticles} cap`
	)
end

--- Grade tiers. The same room is dressed three ways over eleven years: a first
--- year's lesson is bright and soft, a graduating year's is dim and hard. It is
--- the cheapest way to make progression visible in a place the player already
--- walks through every session.
export type Tier = { id: string, minGrade: number, maxGrade: number, warmth: number, accent: number }

Decor.Tiers = {
	{ id = "junior", minGrade = 1, maxGrade = 4, warmth = 1.15, accent = 0x60B078 },
	{ id = "middle", minGrade = 5, maxGrade = 8, warmth = 1, accent = 0x4660BE },
	{ id = "senior", minGrade = 9, maxGrade = 11, warmth = 0.82, accent = 0xB24A58 },
} :: { Tier }

function Decor.tierFor(grade: number): Tier
	for _, tier in Decor.Tiers do
		if grade >= tier.minGrade and grade <= tier.maxGrade then
			return tier
		end
	end
	-- Out of range clamps rather than erroring: a grade this function has never
	-- heard of is a progression bug, and a crash in the decor layer would hide it.
	return if grade < Decor.Tiers[1].minGrade then Decor.Tiers[1] else Decor.Tiers[#Decor.Tiers]
end

return Decor
