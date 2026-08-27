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
--- out of step with it the first time a subject is added.

local CollectionService = game:GetService("CollectionService")
local ProximityPromptService = game:GetService("ProximityPromptService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Workspace = game:GetService("Workspace")

local Strings = require(ReplicatedStorage.Shared.Strings)
local Subjects = require(ReplicatedStorage.Shared.Config.Subjects)
local LessonService = require(script.Parent.LessonService)

local WorldService = {}

local ORIGIN = Vector3.new(0, 0, 0)
local ROOM_WIDTH = 34
local ROOM_DEPTH = 30
local CORRIDOR_WIDTH = 24
local WALL_HEIGHT = 14
local WALL_THICKNESS = 1

local FLOOR_COLOUR = Color3.fromRGB(206, 200, 188)
local CORRIDOR_COLOUR = Color3.fromRGB(188, 182, 170)
local WALL_COLOUR = Color3.fromRGB(232, 228, 220)
local BOARD_COLOUR = Color3.fromRGB(44, 66, 54)
local DESK_COLOUR = Color3.fromRGB(140, 104, 70)
local TEACHER_COLOUR = Color3.fromRGB(70, 96, 190)
local SKIN_COLOUR = Color3.fromRGB(226, 190, 160)

--- Which prompt teaches what. The prompt instance is the key, so a triggered
--- prompt resolves to a subject without trusting anything the client said.
local prompts: { [ProximityPrompt]: { subject: string, kind: string? } } = {}

WorldService.PromptTag = "SubjectPrompt"
WorldService.SubjectAttribute = "Subject"

local function block(
	parent: Instance,
	name: string,
	size: Vector3,
	position: Vector3,
	colour: Color3
): Part
	local part = Instance.new("Part")
	part.Name = name
	part.Anchored = true
	part.Size = size
	part.Position = position
	part.Color = colour
	part.Material = Enum.Material.SmoothPlastic
	part.TopSurface = Enum.SurfaceType.Smooth
	part.BottomSurface = Enum.SurfaceType.Smooth
	part.Parent = parent
	return part
end

local function nameplate(parent: BasePart, text: string)
	local gui = Instance.new("BillboardGui")
	gui.Size = UDim2.fromOffset(220, 44)
	gui.StudsOffsetWorldSpace = Vector3.new(0, 3.4, 0)
	gui.AlwaysOnTop = true
	gui.Parent = parent

	local label = Instance.new("TextLabel")
	label.Size = UDim2.fromScale(1, 1)
	label.BackgroundTransparency = 1
	label.Font = Enum.Font.GothamBold
	label.TextSize = 18
	label.TextColor3 = Color3.fromRGB(255, 255, 255)
	label.TextStrokeTransparency = 0.4
	label.TextScaled = false
	label.Text = text
	label.Parent = gui
end

--- A figure built from parts rather than a rig. It reads as a person standing
--- at the front of a room, and it depends on no asset that has to exist first.
local function buildTeacher(
	parent: Instance,
	position: Vector3,
	subject: string,
	kind: string?
)
	local model = Instance.new("Model")
	model.Name = `Teacher_{subject}`
	model.Parent = parent

	local legs = block(model, "Legs", Vector3.new(2, 3, 1.4), position + Vector3.new(0, 1.5, 0), Color3.fromRGB(52, 58, 72))
	block(model, "Torso", Vector3.new(2.4, 2.8, 1.6), position + Vector3.new(0, 4.4, 0), TEACHER_COLOUR)
	local head = block(model, "Head", Vector3.new(1.4, 1.4, 1.4), position + Vector3.new(0, 6.5, 0), SKIN_COLOUR)
	model.PrimaryPart = legs

	-- The default English name; every player is sent their own on join.
	nameplate(head, Strings.get(`subject.{subject}`, Strings.Fallback))

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

local function buildRoom(parent: Instance, centre: Vector3, subject: string, kind: string?, facing: number)
	local room = Instance.new("Model")
	room.Name = `Room_{subject}`
	room.Parent = parent

	block(room, "Floor", Vector3.new(ROOM_WIDTH, 1, ROOM_DEPTH), centre, FLOOR_COLOUR)

	-- Back and side walls only; the corridor side is the doorway.
	local backZ = centre.Z + facing * (ROOM_DEPTH / 2)
	block(
		room,
		"BackWall",
		Vector3.new(ROOM_WIDTH, WALL_HEIGHT, WALL_THICKNESS),
		Vector3.new(centre.X, centre.Y + WALL_HEIGHT / 2, backZ),
		WALL_COLOUR
	)
	for _, side in { -1, 1 } do
		block(
			room,
			"SideWall",
			Vector3.new(WALL_THICKNESS, WALL_HEIGHT, ROOM_DEPTH),
			Vector3.new(centre.X + side * (ROOM_WIDTH / 2), centre.Y + WALL_HEIGHT / 2, centre.Z),
			WALL_COLOUR
		)
	end

	local board = block(
		room,
		"Board",
		Vector3.new(ROOM_WIDTH * 0.6, 7, 0.4),
		Vector3.new(centre.X, centre.Y + 6, backZ - facing * 0.8),
		BOARD_COLOUR
	)
	nameplate(board, Strings.get(`subject.{subject}`, Strings.Fallback))

	block(
		room,
		"Desk",
		Vector3.new(8, 3, 3),
		Vector3.new(centre.X, centre.Y + 2, backZ - facing * 6),
		DESK_COLOUR
	)

	-- Rows of seats, so the room reads as a classroom rather than an empty box.
	for row = 1, 3 do
		for seat = -1, 1 do
			block(
				room,
				"Seat",
				Vector3.new(3, 2, 3),
				Vector3.new(
					centre.X + seat * 8,
					centre.Y + 1.5,
					backZ - facing * (11 + row * 4)
				),
				DESK_COLOUR
			)
		end
	end

	buildTeacher(room, Vector3.new(centre.X, centre.Y + 0.5, backZ - facing * 9), subject, kind)
end

--- PE and art are not quizzes, so their teacher starts the right thing. The
--- other subjects fall through to a bank lesson.
local function kindFor(subject: string): string?
	if Subjects.allows(subject, "assembly") and not Subjects.allows(subject, "quiz") then
		return "assembly"
	end
	return nil
end

function WorldService.build()
	local school = Instance.new("Model")
	school.Name = "School"
	school.Parent = Workspace

	local rooms = #Subjects.List
	local perSide = math.ceil(rooms / 2)
	local corridorLength = perSide * ROOM_WIDTH

	block(
		school,
		"Corridor",
		Vector3.new(corridorLength, 1, CORRIDOR_WIDTH),
		ORIGIN,
		CORRIDOR_COLOUR
	)

	for index, subject in Subjects.List do
		local side = if index <= perSide then 1 else -1
		local column = if side == 1 then index - 1 else index - perSide - 1
		local x = ORIGIN.X - corridorLength / 2 + ROOM_WIDTH / 2 + column * ROOM_WIDTH
		local z = ORIGIN.Z + side * (CORRIDOR_WIDTH / 2 + ROOM_DEPTH / 2)
		buildRoom(school, Vector3.new(x, ORIGIN.Y, z), subject.id, kindFor(subject.id), side)
	end

	local spawnPart = Instance.new("SpawnLocation")
	spawnPart.Name = "SchoolSpawn"
	spawnPart.Anchored = true
	spawnPart.Size = Vector3.new(12, 1, 12)
	spawnPart.Position = ORIGIN + Vector3.new(0, 1, 0)
	spawnPart.Color = Color3.fromRGB(120, 150, 190)
	spawnPart.Material = Enum.Material.SmoothPlastic
	spawnPart.TopSurface = Enum.SurfaceType.Smooth
	spawnPart.Duration = 0
	spawnPart.Parent = school

	return school
end

function WorldService.start()
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
