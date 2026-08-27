--!strict
--- Geometry primitives for the school.
---
--- Everything the world is made of goes through here, which buys two things
--- that matter more than tidiness:
---
---   * Every part is anchored, non-colliding where it should be, and CastShadow
---     off unless it earns a shadow. Thirty rooms of shadow-casting props is a
---     measurable frame cost, and "we forgot on one prop" is invisible until it
---     is everywhere.
---   * Rotation exists. The old builder placed axis-aligned blocks by Position,
---     so a room could only face two directions. Anything angled -- a staircase,
---     a raked auditorium, a roof -- needs CFrame, and a builder that offers only
---     Position quietly teaches the caller not to ask.

local CollectionService = game:GetService("CollectionService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Strings = require(ReplicatedStorage.Shared.Strings)

local Build = {}

--- Signs that carry a translatable key are tagged with this and relabelled on
--- each client. See Build.signKey.
Build.SignTag = "WorldSign"
Build.SignKeyAttribute = "StringKey"

--- Config carries colours as packed 0xRRGGBB integers and materials as strings,
--- because config in this project imports nothing from the engine -- that is what
--- lets the unit tests execute it directly. The conversion back happens here and
--- only here, so exactly one file knows both representations.
function Build.colour(packed: number): Color3
	return Color3.fromRGB(
		bit32.band(bit32.rshift(packed, 16), 0xFF),
		bit32.band(bit32.rshift(packed, 8), 0xFF),
		bit32.band(packed, 0xFF)
	)
end

--- An unknown material name falls back to plastic rather than erroring: a typo
--- in a theme should produce a plain-looking room, not a school that fails to
--- build. The typo is caught by tools/check_decor.py, where it is cheap.
function Build.material(name: string): Enum.Material
	local material = (Enum.Material :: any)[name]
	return if typeof(material) == "EnumItem" then material else Enum.Material.SmoothPlastic
end

export type Options = {
	material: Enum.Material?,
	transparency: number?,
	reflectance: number?,
	canCollide: boolean?,
	castShadow: boolean?,
	cornerRadius: number?,
}

local NO_OPTIONS: Options = {}

--- The one place a Part is constructed. `cf` carries position and rotation
--- together, because splitting them is how half a building ends up axis-aligned.
function Build.part(
	parent: Instance,
	name: string,
	size: Vector3,
	cf: CFrame,
	colour: Color3,
	options: Options?
): Part
	local o = options or NO_OPTIONS
	local part = Instance.new("Part")
	part.Name = name
	part.Anchored = true
	part.Size = size
	part.CFrame = cf
	part.Color = colour
	part.Material = o.material or Enum.Material.SmoothPlastic
	part.Transparency = o.transparency or 0
	part.Reflectance = o.reflectance or 0
	part.CanCollide = if o.canCollide == nil then true else o.canCollide
	-- Off by default. A prop that wants a shadow says so; the other four hundred
	-- do not pay for one.
	part.CastShadow = o.castShadow == true
	part.TopSurface = Enum.SurfaceType.Smooth
	part.BottomSurface = Enum.SurfaceType.Smooth
	part.Parent = parent
	return part
end

--- The common case: axis-aligned, positioned by its centre.
function Build.block(
	parent: Instance,
	name: string,
	size: Vector3,
	position: Vector3,
	colour: Color3,
	options: Options?
): Part
	return Build.part(parent, name, size, CFrame.new(position), colour, options)
end

--- A pane of glass. Separated out because a window that forgets CanCollide=false
--- is a wall, and a window that forgets CastShadow is a dark room.
function Build.window(parent: Instance, name: string, size: Vector3, position: Vector3): Part
	return Build.block(parent, name, size, position, Color3.fromRGB(198, 224, 236), {
		material = Enum.Material.Glass,
		transparency = 0.72,
		reflectance = 0.12,
		canCollide = false,
		castShadow = false,
	})
end

--- Floating text over a part, for text that is not translatable -- a number, a
--- player's name. Anything with a string key goes through Build.signKey instead.
---
--- `worldOffset` lifts it clear of whatever it labels.
function Build.sign(
	parent: BasePart,
	text: string,
	worldOffset: number,
	colour: Color3,
	size: number
): TextLabel
	local gui = Instance.new("BillboardGui")
	gui.Name = "Sign"
	gui.Size = UDim2.fromOffset(260, 48)
	gui.StudsOffsetWorldSpace = Vector3.new(0, worldOffset, 0)
	gui.AlwaysOnTop = false
	-- Signs stop being readable long before they stop being drawn. Cutting them
	-- at 90 studs is a corridor's worth of visibility and a lot of saved draw.
	gui.MaxDistance = 90
	gui.Parent = parent

	local label = Instance.new("TextLabel")
	label.Name = "Text"
	label.Size = UDim2.fromScale(1, 1)
	label.BackgroundTransparency = 1
	label.Font = Enum.Font.GothamBold
	label.TextSize = size
	label.TextColor3 = colour
	label.TextStrokeTransparency = 0.45
	label.Text = text
	label.Parent = gui
	return label
end

--- A sign whose text comes from the string table.
---
--- The world is built once on the server, so a sign's text is a single value
--- shared by everyone in it -- exactly the trap the ProximityPrompt labels fell
--- into. Writing a language here would pick that language for the whole server.
--- So the server writes the fallback and tags the label with its key, and each
--- client rewrites it in its own language. A player who never gets a client
--- controller still reads a real word rather than a blank sign.
function Build.signKey(
	parent: BasePart,
	key: string,
	worldOffset: number,
	colour: Color3,
	size: number
): TextLabel
	local label = Build.sign(parent, Strings.get(key, Strings.Fallback), worldOffset, colour, size)
	label:SetAttribute(Build.SignKeyAttribute, key)
	CollectionService:AddTag(label, Build.SignTag)
	return label
end

--- A ceiling light: the fitting you can see, and the light it casts.
function Build.lamp(
	parent: Instance,
	position: Vector3,
	colour: Color3,
	brightness: number,
	range: number
): Part
	local fitting = Build.block(parent, "Lamp", Vector3.new(6, 0.4, 2), position, colour, {
		material = Enum.Material.Neon,
		canCollide = false,
		castShadow = false,
	})

	local light = Instance.new("PointLight")
	light.Color = colour
	light.Brightness = brightness
	light.Range = range
	-- Shadows are per-light and expensive, and a classroom ceiling lamp casts
	-- almost nothing worth seeing. The sun through the windows does that work.
	light.Shadows = false
	light.Parent = fitting

	return fitting
end

--- The ambient effect for a room. Returns nil for "none" so a caller can tell
--- an unthemed room from a themed one without comparing strings.
function Build.emitter(
	parent: BasePart,
	effect: string,
	emission: {
		rate: number,
		lifetime: number,
		speed: number,
		size: number,
		transparency: number,
		drift: number,
		spread: number,
	},
	colour: Color3
): ParticleEmitter?
	if effect == "none" then
		return nil
	end

	local emitter = Instance.new("ParticleEmitter")
	emitter.Name = `Effect_{effect}`
	emitter.Color = ColorSequence.new(colour)
	emitter.Rate = emission.rate
	emitter.Lifetime = NumberRange.new(emission.lifetime * 0.7, emission.lifetime)
	emitter.Speed = NumberRange.new(emission.speed * 0.5, emission.speed)
	emitter.SpreadAngle = Vector2.new(emission.spread, emission.spread)
	emitter.Acceleration = Vector3.new(0, emission.drift, 0)
	emitter.Rotation = NumberRange.new(0, 360)
	emitter.RotSpeed = NumberRange.new(-30, 30)
	emitter.LightEmission = if effect == "sparks" then 0.9 else 0.1
	-- Fade in and out rather than popping. Particles that appear at full opacity
	-- read as a glitch, which is the one thing ambient dressing must never do.
	emitter.Size = NumberSequence.new({
		NumberSequenceKeypoint.new(0, 0),
		NumberSequenceKeypoint.new(0.25, emission.size),
		NumberSequenceKeypoint.new(1, 0),
	})
	emitter.Transparency = NumberSequence.new({
		NumberSequenceKeypoint.new(0, 1),
		NumberSequenceKeypoint.new(0.2, emission.transparency),
		NumberSequenceKeypoint.new(0.85, emission.transparency),
		NumberSequenceKeypoint.new(1, 1),
	})
	emitter.Parent = parent
	return emitter
end

--- A run of stairs, built as steps rather than a ramp so it reads as a school
--- and not a car park.
function Build.stairs(
	parent: Instance,
	name: string,
	base: Vector3,
	steps: number,
	stepRise: number,
	stepRun: number,
	width: number,
	colour: Color3,
	options: Options?
)
	for step = 1, steps do
		Build.block(
			parent,
			`{name}_{step}`,
			Vector3.new(width, stepRise, stepRun),
			base + Vector3.new(0, (step - 0.5) * stepRise, (step - 0.5) * stepRun),
			colour,
			options
		)
	end
end

return Build
