--!strict
--- Obstacle courses for PE: the module catalogue, the difficulty curve, and the
--- rules a teacher's course has to satisfy.
---
--- This is the one subject where a teacher creates without typing a word. A
--- course is an ordered list of prefab module ids and a target grade; assembling
--- prefabs is explicitly not free-form user creation, so nothing here goes near
--- the moderation queue and a course publishes the instant it is saved.
---
--- Difficulty is not a property of a module, it is a property of the grade. The
--- same gap module is four studs wide for a first-year and eighteen for a
--- final-year, which is what makes one catalogue serve the whole school.

local Obstacles = {}

Obstacles.MaxGrade = 11

--- A teacher may set a course one grade either side of their class, and no
--- further. The quality factor would eventually punish a trivial course through
--- its pass rate, but that takes twenty attempts to notice; this refuses the
--- exploit outright, before any student wastes time on it.
Obstacles.GradeWindow = 1

export type Module = {
	id: string,
	--- Earliest grade this module may appear in. Keeps the hard toys out of the
	--- hands of teachers running a second-year class.
	minGrade: number,
	--- Studs of course length this module consumes when built.
	length: number,
	--- Whether the prefab-pack pass is needed to place this module.
	---
	--- The pass sells variety, never difficulty or advantage: a student running a
	--- paid teacher's course meets different shapes, not harder ones, and the
	--- grade window still decides how hard the course may be. Selling difficulty
	--- would make a bought course pay more, which is the one thing the payout
	--- formula must not be able to buy.
	premium: boolean,
	displayKey: string,
}

Obstacles.Modules = {
	{ id = "gap", minGrade = 1, length = 40, premium = false, displayKey = "module.gap" },
	{ id = "narrowBeam", minGrade = 1, length = 48, premium = false, displayKey = "module.narrowBeam" },
	{ id = "movingPlatform", minGrade = 2, length = 52, premium = false, displayKey = "module.movingPlatform" },
	{ id = "vanishingTiles", minGrade = 4, length = 56, premium = false, displayKey = "module.vanishingTiles" },
	{ id = "spinner", minGrade = 6, length = 44, premium = false, displayKey = "module.spinner" },
	{ id = "hazardField", minGrade = 8, length = 60, premium = false, displayKey = "module.hazardField" },
	{ id = "pendulum", minGrade = 3, length = 50, premium = true, displayKey = "module.pendulum" },
	{ id = "conveyor", minGrade = 2, length = 54, premium = true, displayKey = "module.conveyor" },
	{ id = "steppingStones", minGrade = 5, length = 58, premium = true, displayKey = "module.steppingStones" },
} :: { Module }


local moduleById: { [string]: Module } = {}
for _, entry in Obstacles.Modules do
	moduleById[entry.id] = entry
end

function Obstacles.getModule(id: string): Module?
	return moduleById[id]
end

--- Normalised difficulty, 0 at first grade and 1 at the last.
---
--- The exponent bends the curve so the early grades stay gentle and the last
--- few climb steeply. A linear ramp would make the eleventh grade merely twice
--- the fifth, when what is wanted is for it to be genuinely hard.
local DIFFICULTY_EXPONENT = 1.35

function Obstacles.difficulty(grade: number): number
	local clamped = math.clamp(grade, 1, Obstacles.MaxGrade)
	return ((clamped - 1) / (Obstacles.MaxGrade - 1)) ^ DIFFICULTY_EXPONENT
end

local function lerp(from: number, to: number, t: number): number
	return from + (to - from) * t
end

export type Params = {
	grade: number,
	difficulty: number,
	--- Studs to clear on a jump. Roblox's default character clears roughly twenty
	--- at a full run, so the top of this range is at the edge of possible.
	gapStuds: number,
	--- Width of a beam walkway. Character width is about two studs.
	beamWidth: number,
	platformSpeed: number,
	--- How long a tile stays under you after you touch it.
	vanishSeconds: number,
	spinnerSpeed: number,
	hazardDensity: number,
	moduleCount: number,
	--- Modules between checkpoints. Zero means none at all: reach the end or
	--- start over.
	checkpointEvery: number,
	timeLimitSeconds: number,
}

function Obstacles.paramsForGrade(grade: number): Params
	local clamped = math.clamp(math.floor(grade), 1, Obstacles.MaxGrade)
	local t = Obstacles.difficulty(clamped)
	local moduleCount = math.round(lerp(5, 12, t))

	local checkpointEvery
	if clamped <= 3 then
		checkpointEvery = 1
	elseif clamped <= 6 then
		checkpointEvery = 2
	elseif clamped <= 9 then
		checkpointEvery = 3
	else
		checkpointEvery = 0
	end

	return {
		grade = clamped,
		difficulty = t,
		gapStuds = lerp(4, 18, t),
		beamWidth = lerp(6, 1.5, t),
		platformSpeed = lerp(3, 24, t),
		vanishSeconds = lerp(2.5, 0.55, t),
		spinnerSpeed = lerp(0.6, 4, t),
		hazardDensity = lerp(0.1, 0.6, t),
		moduleCount = moduleCount,
		checkpointEvery = checkpointEvery,
		timeLimitSeconds = moduleCount * lerp(22, 12, t),
	}
end

--- The grades a teacher running `classGrade` may target.
function Obstacles.allowedGrades(classGrade: number): (number, number)
	local centre = math.clamp(math.floor(classGrade), 1, Obstacles.MaxGrade)
	return math.max(1, centre - Obstacles.GradeWindow),
		math.min(Obstacles.MaxGrade, centre + Obstacles.GradeWindow)
end

--- Modules a teacher may place at this grade.
---
--- `hasPrefabPack` is passed in rather than read here, so this stays pure and the
--- tests can run it. Omitting it lists everything the grade allows, which is what
--- the builder wants when it draws locked modules alongside owned ones.
function Obstacles.modulesForGrade(grade: number, hasPrefabPack: boolean?): { Module }
	local available: { Module } = {}
	for _, entry in Obstacles.Modules do
		if entry.minGrade > grade then
			continue
		end
		if entry.premium and hasPrefabPack == false then
			continue
		end
		table.insert(available, entry)
	end
	return available
end

--- A course of twelve identical gaps is not a course, it is one obstacle typed
--- twelve times, and it is the cheapest way to make a "hard" course that is
--- actually trivial. Requiring variety costs the honest teacher nothing.
function Obstacles.requiredDistinctTypes(grade: number, moduleCount: number): number
	local available = #Obstacles.modulesForGrade(grade)
	return math.min(available, math.max(2, math.ceil(moduleCount / 4)))
end

export type Validation = { ok: boolean, reason: string? }

function Obstacles.validateCourse(
	classGrade: number,
	courseGrade: number,
	moduleIds: { string },
	hasPrefabPack: boolean?
): Validation
	local low, high = Obstacles.allowedGrades(classGrade)
	if courseGrade < low or courseGrade > high then
		return { ok = false, reason = "gradeOutOfWindow" }
	end

	local params = Obstacles.paramsForGrade(courseGrade)
	-- A shorter course than the grade calls for is the other way to make it easy,
	-- so the count is pinned rather than merely capped.
	if #moduleIds < params.moduleCount then
		return { ok = false, reason = "tooShort" }
	end
	if #moduleIds > params.moduleCount + 4 then
		return { ok = false, reason = "tooLong" }
	end

	local distinct: { [string]: boolean } = {}
	local distinctCount = 0
	for _, id in moduleIds do
		local entry = moduleById[id]
		if entry == nil then
			return { ok = false, reason = "unknownModule" }
		end
		if entry.minGrade > courseGrade then
			return { ok = false, reason = "moduleTooAdvanced" }
		end
		-- Checked here rather than only in the builder UI: the client picks the
		-- modules, and a client that decided which ones it was allowed to pick
		-- would be a client deciding what it owns.
		if entry.premium and hasPrefabPack ~= true then
			return { ok = false, reason = "needsPrefabPack" }
		end
		if not distinct[id] then
			distinct[id] = true
			distinctCount += 1
		end
	end

	if distinctCount < Obstacles.requiredDistinctTypes(courseGrade, #moduleIds) then
		return { ok = false, reason = "tooRepetitive" }
	end

	return { ok = true, reason = nil }
end

return Obstacles
