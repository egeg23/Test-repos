--!strict
--- Builds the school, and the teachers who are always in it.
---
--- Two problems in one. A player was arriving on an empty baseplate with
--- floating panels and nowhere to be; and the plan's answer to the cold start --
--- teachers on duty round the clock so the school is never empty -- had never
--- been built, leaving the bank lessons reachable only through a menu.
---
--- Both are solved by the same thing: a corridor of classrooms with somebody
--- standing in each. Walking up to the maths teacher and pressing a key is a
--- game; picking "maths" out of a list is a form.
---
--- Everything is built from parts at run time rather than placed in the level.
--- The subject list is config, and a school whose rooms are hand-placed drifts
--- out of step with it the first time a subject is added. This file is now only
--- the layout and the wiring: geometry lives in World/Build, rooms in
--- World/Rooms, the building's outside in World/Exterior, and what any of it
--- looks like in Config/Decor.

local CollectionService = game:GetService("CollectionService")
local Lighting = game:GetService("Lighting")
local ProximityPromptService = game:GetService("ProximityPromptService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Workspace = game:GetService("Workspace")

local Campus = require(ReplicatedStorage.Shared.Config.Campus)
local Subjects = require(ReplicatedStorage.Shared.Config.Subjects)
local Build = require(script.Parent.Parent.World.Build)
local Exterior = require(script.Parent.Parent.World.Exterior)
local Rooms = require(script.Parent.Parent.World.Rooms)
local LessonService = require(script.Parent.LessonService)

local WorldService = {}

local ORIGIN = Vector3.new(0, 0, 0)
local TEACHER_COLOUR = Color3.fromRGB(70, 96, 190)
local SKIN_COLOUR = Color3.fromRGB(226, 190, 160)

--- Which prompt teaches what. The prompt instance is the key, so a triggered
--- prompt resolves to a subject without trusting anything the client said.
local prompts: { [ProximityPrompt]: { subject: string, kind: string? } } = {}

WorldService.PromptTag = "SubjectPrompt"
WorldService.SubjectAttribute = "Subject"

--- A figure built from parts rather than a rig. It reads as a person standing
--- at the front of a room, and it depends on no asset that has to exist first.
local function buildTeacher(
	parent: Instance,
	position: Vector3,
	subject: string,
	facing: number,
	accent: Color3,
	kind: string?
)
	local model = Instance.new("Model")
	model.Name = `Teacher_{subject}`
	model.Parent = parent

	-- Turned to face the room rather than the back wall. The old builder placed
	-- the figure by Position only, so every teacher in the school faced +Z and
	-- half of them had their back to the class.
	local base = CFrame.new(position) * CFrame.Angles(0, if facing > 0 then math.pi else 0, 0)

	local legs = Build.part(model, "Legs", Vector3.new(2, 3, 1.4), base * CFrame.new(0, 1.5, 0), Color3.fromRGB(52, 58, 72))
	Build.part(model, "Torso", Vector3.new(2.4, 2.8, 1.6), base * CFrame.new(0, 4.4, 0), TEACHER_COLOUR, { castShadow = true })
	-- A stripe in the subject's colour, so an NPC is identifiable from the door.
	Build.part(model, "Sash", Vector3.new(2.5, 0.7, 1.7), base * CFrame.new(0, 5.2, 0), accent, { castShadow = false })
	for _, side in { -1, 1 } do
		Build.part(model, "Arm", Vector3.new(0.8, 2.6, 0.8), base * CFrame.new(side * 1.6, 4.4, 0), TEACHER_COLOUR, { castShadow = false })
	end
	local head = Build.part(model, "Head", Vector3.new(1.4, 1.4, 1.4), base * CFrame.new(0, 6.5, 0), SKIN_COLOUR, { castShadow = true })
	model.PrimaryPart = legs

	-- The default English name; every player is sent their own on join.
	Build.signKey(head, `subject.{subject}`, 3.2, Color3.fromRGB(255, 255, 255), 18)

	local prompt = Instance.new("ProximityPrompt")
	prompt.HoldDuration = 0.2
	prompt.MaxActivationDistance = 12
	prompt.RequiresLineOfSight = false
	-- The subject travels on the instance so the client can label it. The prompt
	-- itself is replicated, which means its text is one value shared by everyone:
	-- writing a player's language into it on the server would set that language
	-- for the whole server. Labelling is the client's job, locally.
	prompt:SetAttribute(WorldService.SubjectAttribute, subject)
	CollectionService:AddTag(prompt, WorldService.PromptTag)
	prompt.Parent = head

	prompts[prompt] = { subject = subject, kind = kind }
end

--- PE and art are not quizzes, so their teacher starts the right thing. The
--- other subjects fall through to a bank lesson.
local function kindFor(subject: string): string?
	if Subjects.allows(subject, "assembly") and not Subjects.allows(subject, "quiz") then
		return "assembly"
	end
	return nil
end

--- Daylight, and the haze that keeps a big flat interior from looking like one.
local function lighting()
	Lighting.Ambient = Color3.fromRGB(112, 112, 122)
	Lighting.OutdoorAmbient = Color3.fromRGB(136, 140, 152)
	Lighting.Brightness = 2.4
	Lighting.ClockTime = 10.5
	Lighting.GeographicLatitude = 41
	Lighting.ExposureCompensation = 0.15
	Lighting.GlobalShadows = true

	-- Cleared and rebuilt rather than edited in place, so a rebuild in Studio
	-- does not stack four Atmospheres on top of each other.
	for _, existing in Lighting:GetChildren() do
		if existing:IsA("Atmosphere") or existing:IsA("PostEffect") or existing:IsA("Sky") then
			existing:Destroy()
		end
	end

	local atmosphere = Instance.new("Atmosphere")
	atmosphere.Density = 0.32
	atmosphere.Offset = 0.1
	atmosphere.Color = Color3.fromRGB(214, 214, 222)
	atmosphere.Decay = Color3.fromRGB(150, 154, 170)
	atmosphere.Glare = 0.2
	atmosphere.Haze = 1.2
	atmosphere.Parent = Lighting

	local bloom = Instance.new("BloomEffect")
	bloom.Intensity = 0.4
	bloom.Size = 20
	bloom.Threshold = 1.4
	bloom.Parent = Lighting

	local colour = Instance.new("ColorCorrectionEffect")
	colour.Brightness = 0.02
	colour.Contrast = 0.08
	colour.Saturation = 0.06
	colour.Parent = Lighting

	-- Only inside gets depth of field, and only barely. Anything stronger turns
	-- the far end of a corridor into soup on a phone.
	local blur = Instance.new("DepthOfFieldEffect")
	blur.FarIntensity = 0.08
	blur.NearIntensity = 0
	blur.FocusDistance = 40
	blur.InFocusRadius = 60
	blur.Parent = Lighting
end

--- Room footprints, in the order they appear down the corridor. Depths are
--- multiples of the classroom depth, matching what each Rooms.* builder makes --
--- a number here that disagreed with the builder would put a wall through a room.
local HALL_SIZES = {
	gym = { width = Rooms.Width * 2, depth = Rooms.Depth * 1.6 },
	library = { width = Rooms.Width * 1.5, depth = Rooms.Depth * 1.4 },
	assembly = { width = Rooms.Width * 2.2, depth = Rooms.Depth * 1.8 },
	staffroom = { width = Rooms.Width, depth = Rooms.Depth * 0.8 },
}

function WorldService.build()
	local school = Instance.new("Model")
	school.Name = "School"
	school.Parent = Workspace

	-- Rooms are laid out with a cursor per side rather than by index arithmetic.
	-- The halls are different widths from the classrooms and from each other, so
	-- an index-times-width layout silently overlapped them -- which is exactly
	-- the bug a cursor cannot have.
	local cursor = { [1] = 0, [-1] = 0 }
	local deepest = { [1] = 0, [-1] = 0 }

	--- Reserves the next bay on `side` and returns where its centre goes.
	local function place(side: number, width: number, depth: number): Vector3
		local x = cursor[side] + width / 2
		cursor[side] += width
		deepest[side] = math.max(deepest[side], depth)
		return Vector3.new(x, ORIGIN.Y, side * (Rooms.CorridorWidth / 2 + depth / 2))
	end

	local perSide = math.ceil(#Subjects.List / 2)
	local placements: { { subject: any, centre: Vector3, side: number } } = {}
	for index, subject in Subjects.List do
		local side = if index <= perSide then 1 else -1
		table.insert(placements, {
			subject = subject,
			centre = place(side, Rooms.Width, Rooms.Depth),
			side = side,
		})
	end

	local gymCentre = place(1, HALL_SIZES.gym.width, HALL_SIZES.gym.depth)
	local libraryCentre = place(1, HALL_SIZES.library.width, HALL_SIZES.library.depth)
	local assemblyCentre = place(-1, HALL_SIZES.assembly.width, HALL_SIZES.assembly.depth)
	local staffroomCentre = place(-1, HALL_SIZES.staffroom.width, HALL_SIZES.staffroom.depth)

	local corridorLength = math.max(cursor[1], cursor[-1])
	local bounds: Exterior.Bounds = {
		minX = 0,
		maxX = corridorLength,
		minZ = -(Rooms.CorridorWidth / 2 + deepest[-1]),
		maxZ = Rooms.CorridorWidth / 2 + deepest[1],
	}

	Build.block(
		school,
		"Corridor",
		Vector3.new(corridorLength, 1, Rooms.CorridorWidth),
		Vector3.new(corridorLength / 2, ORIGIN.Y, 0),
		Color3.fromRGB(198, 192, 182),
		{ material = Enum.Material.Concrete }
	)
	Build.block(
		school,
		"CorridorRunner",
		Vector3.new(corridorLength, 0.06, 6),
		Vector3.new(corridorLength / 2, ORIGIN.Y + 0.53, 0),
		Color3.fromRGB(150, 92, 84),
		{ material = Enum.Material.Carpet, canCollide = false, castShadow = false }
	)
	Build.block(
		school,
		"CorridorCeiling",
		Vector3.new(corridorLength, 0.6, Rooms.CorridorWidth),
		Vector3.new(corridorLength / 2, ORIGIN.Y + Rooms.WallHeight, 0),
		Color3.fromRGB(232, 228, 220),
		{ castShadow = false }
	)
	for bay = 0, math.floor(corridorLength / Rooms.Width) do
		Build.lamp(
			school,
			Vector3.new(bay * Rooms.Width + Rooms.Width / 2, Rooms.WallHeight - 1, 0),
			Color3.fromRGB(248, 246, 240),
			1.4,
			38
		)
	end

	for _, entry in placements do
		local room = Rooms.classroom(
			school,
			entry.centre,
			entry.subject.id,
			entry.side,
			entry.subject.displayKey
		)
		buildTeacher(
			school,
			room.front,
			entry.subject.id,
			entry.side,
			room.palette.trim,
			kindFor(entry.subject.id)
		)
	end

	local gym = Rooms.gym(school, gymCentre, 1, "world.gym")
	local assembly =
		Rooms.assembly(school, assemblyCentre, -1, "world.assembly")
	Rooms.library(school, libraryCentre, 1, "world.library")
	Rooms.staffroom(school, staffroomCentre, -1, "world.staffroom")

	-- The gym teacher runs obstacle courses. The library and staff room have no
	-- NPC: a librarian who started "a lesson" would have to pick a subject, and
	-- picking one arbitrarily is the menu this whole world exists to replace.
	buildTeacher(school, gym.front, "pe", 1, gym.palette.trim, kindFor("pe"))

	if assembly.stage ~= nil then
		Build.signKey(assembly.stage, "campus.title", 6, Color3.fromRGB(255, 236, 228), 28)
	end

	Exterior.grounds(school, bounds)
	Exterior.facade(
		school,
		bounds,
		Rooms.WallHeight + 8,
		Campus.Mottos[1]
	)
	local _, board = Exterior.entranceFurniture(school, bounds)
	Build.signKey(board, "campus.title", 5, Color3.fromRGB(246, 240, 226), 20)

	local spawnPart = Instance.new("SpawnLocation")
	spawnPart.Name = "SchoolSpawn"
	spawnPart.Anchored = true
	spawnPart.Size = Vector3.new(16, 1, 16)
	-- On the path, outside the doors. Spawning in the corridor would skip the
	-- building, and the building is most of what is here.
	spawnPart.Position = Exterior.spawnPosition(bounds)
	spawnPart.Color = Color3.fromRGB(198, 192, 180)
	spawnPart.Material = Enum.Material.Concrete
	spawnPart.TopSurface = Enum.SurfaceType.Smooth
	spawnPart.Duration = 0
	spawnPart.Parent = school

	return school
end

function WorldService.start()
	lighting()
	WorldService.build()

	ProximityPromptService.PromptTriggered:Connect(function(prompt: ProximityPrompt, player: Player)
		local target = prompts[prompt]
		if target == nil then
			return
		end
		LessonService.startFromWorld(player, target.subject, target.kind)
	end)
end

return WorldService
