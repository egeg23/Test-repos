--!strict
--- Obstacle courses: building them, running them, and refusing to be cheated.
---
--- Courses are built per run in their own lane, far from the school, and torn
--- down when the run ends. Two students running the same course never share
--- geometry, so one player's vanished tile is not another player's hole.
---
--- The run is validated on the server. Checkpoints must be reached in order, and
--- each leg has a floor on how fast it can plausibly be covered -- a character
--- runs at sixteen studs a second, so the floor is set against forty and still
--- catches a teleport, which covers the distance in no time at all.

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local Workspace = game:GetService("Workspace")

local Build = require(script.Parent.Parent.World.Build)
local Decor = require(ReplicatedStorage.Shared.Config.Decor)
local Obstacles = require(ReplicatedStorage.Shared.Config.Obstacles)
local Remotes = require(ReplicatedStorage.Shared.Remotes)
local Types = require(ReplicatedStorage.Shared.Types)
local ClassService = require(script.Parent.ClassService)
local RewardService = require(script.Parent.RewardService)

local ObstacleService = {}

local COURSE_ORIGIN = Vector3.new(0, 500, 4000)
local LANE_SPACING = 200
local MAX_LANES = 24
local PLATFORM_WIDTH = 16
local PLATFORM_THICKNESS = 1
--- Falling this far below the lane ends the attempt at that obstacle.
local FALL_DISTANCE = 60
--- Generous: a character runs at 16 studs a second. Anything faster than this is
--- not a fast player.
local IMPLAUSIBLE_SPEED = 40
--- Horizontal studs per second no single frame may exceed. Far above running
--- speed so a spinner's knockback and a long jump both pass, far below a
--- teleport, which crosses the whole course between two frames.
local IMPLAUSIBLE_FRAME_SPEED = 140
--- How far above the lane a player may legitimately get. A jump reaches a few
--- studs and a spinner throws them further; anything past this is flying over
--- the course rather than running it.
local CEILING_HEIGHT = 40
--- Slack around the built course, so brushing the edge of a platform is not an
--- accusation.
local BOUNDS_MARGIN = 60

local COLOUR_PLATFORM = Color3.fromRGB(96, 104, 124)
local COLOUR_BEAM = Color3.fromRGB(120, 132, 160)
local COLOUR_MOVING = Color3.fromRGB(80, 130, 200)
local COLOUR_TILE = Color3.fromRGB(150, 140, 90)
local COLOUR_HAZARD = Color3.fromRGB(190, 70, 70)
local COLOUR_CHECKPOINT = Color3.fromRGB(80, 180, 110)

type Animated = {
	part: BasePart,
	kind: "slide" | "spin",
	origin: Vector3,
	speed: number,
	range: number,
	phase: number,
}

type Run = {
	player: Player,
	lane: number,
	model: Model,
	subject: string,
	statKey: string,
	teacherUserId: number,
	classMembers: number,
	teacherRating: number,
	translated: boolean,
	params: Obstacles.Params,
	checkpoints: { BasePart },
	--- Index of the last checkpoint reached, 0 before the first.
	reached: number,
	lastCheckpointCFrame: CFrame,
	startedAt: number,
	legStartedAt: number,
	legLength: number,
	--- Horizontal box the run is allowed to happen inside, plus a ceiling.
	--- Leaving it means going over the obstacles rather than through them.
	minX: number,
	maxX: number,
	maxZ: number,
	ceilingY: number,
	--- Last sampled position, for the per-frame distance check.
	lastPosition: Vector3?,
	animated: { Animated },
	finished: boolean,
}

local runs: { [Player]: Run } = {}
local lanesInUse: { [number]: boolean } = {}
local heartbeat: RBXScriptConnection? = nil

local function takeLane(): number?
	for lane = 1, MAX_LANES do
		if not lanesInUse[lane] then
			lanesInUse[lane] = true
			return lane
		end
	end
	return nil
end

local function laneOrigin(lane: number): Vector3
	return COURSE_ORIGIN + Vector3.new(0, 0, (lane - 1) * LANE_SPACING)
end

local function makePart(
	parent: Instance,
	size: Vector3,
	position: Vector3,
	colour: Color3
): Part
	local part = Instance.new("Part")
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

--- Each builder lays its geometry starting at `x` and returns how many studs of
--- course it consumed, so the caller never has to know a module's shape.
type BuildContext = {
	model: Model,
	origin: Vector3,
	params: Obstacles.Params,
	animated: { Animated },
	hazards: { BasePart },
	tiles: { BasePart },
}

local builders: { [string]: (BuildContext, number) -> number } = {}

builders.gap = function(context, x)
	local entry = 14
	local exit = 14
	local gap = context.params.gapStuds
	makePart(
		context.model,
		Vector3.new(entry, PLATFORM_THICKNESS, PLATFORM_WIDTH),
		context.origin + Vector3.new(x + entry / 2, 0, 0),
		COLOUR_PLATFORM
	)
	makePart(
		context.model,
		Vector3.new(exit, PLATFORM_THICKNESS, PLATFORM_WIDTH),
		context.origin + Vector3.new(x + entry + gap + exit / 2, 0, 0),
		COLOUR_PLATFORM
	)
	return entry + gap + exit
end

builders.narrowBeam = function(context, x)
	local length = 40
	makePart(
		context.model,
		Vector3.new(length, PLATFORM_THICKNESS, context.params.beamWidth),
		context.origin + Vector3.new(x + length / 2, 0, 0),
		COLOUR_BEAM
	)
	return length
end

builders.movingPlatform = function(context, x)
	local pad = 8
	local void = 26
	makePart(
		context.model,
		Vector3.new(pad, PLATFORM_THICKNESS, PLATFORM_WIDTH),
		context.origin + Vector3.new(x + pad / 2, 0, 0),
		COLOUR_PLATFORM
	)
	makePart(
		context.model,
		Vector3.new(pad, PLATFORM_THICKNESS, PLATFORM_WIDTH),
		context.origin + Vector3.new(x + pad + void + pad / 2, 0, 0),
		COLOUR_PLATFORM
	)

	local centre = context.origin + Vector3.new(x + pad + void / 2, 0, 0)
	local platform = makePart(
		context.model,
		Vector3.new(14, PLATFORM_THICKNESS, 14),
		centre,
		COLOUR_MOVING
	)
	table.insert(context.animated, {
		part = platform,
		kind = "slide",
		origin = centre,
		speed = context.params.platformSpeed,
		range = 22,
		phase = 0,
	})
	return pad + void + pad
end

builders.vanishingTiles = function(context, x)
	local tileLength = 7
	local spacing = 2
	local count = 6
	for index = 0, count - 1 do
		local offset = x + index * (tileLength + spacing) + tileLength / 2
		local tile = makePart(
			context.model,
			Vector3.new(tileLength, PLATFORM_THICKNESS, 10),
			context.origin + Vector3.new(offset, 0, 0),
			COLOUR_TILE
		)
		table.insert(context.tiles, tile)
	end
	return count * (tileLength + spacing)
end

builders.spinner = function(context, x)
	local length = 44
	makePart(
		context.model,
		Vector3.new(length, PLATFORM_THICKNESS, PLATFORM_WIDTH),
		context.origin + Vector3.new(x + length / 2, 0, 0),
		COLOUR_PLATFORM
	)

	local centre = context.origin + Vector3.new(x + length / 2, 2, 0)
	local bar = makePart(context.model, Vector3.new(2, 3, 30), centre, COLOUR_HAZARD)
	bar.CanCollide = false
	table.insert(context.animated, {
		part = bar,
		kind = "spin",
		origin = centre,
		speed = context.params.spinnerSpeed,
		range = 0,
		phase = 0,
	})
	table.insert(context.hazards, bar)
	return length
end

builders.hazardField = function(context, x)
	local length = 60
	makePart(
		context.model,
		Vector3.new(length, PLATFORM_THICKNESS, PLATFORM_WIDTH),
		context.origin + Vector3.new(x + length / 2, 0, 0),
		COLOUR_PLATFORM
	)

	local slots = 12
	local hazardCount = math.max(1, math.floor(slots * context.params.hazardDensity))
	local step = length / slots
	for index = 0, hazardCount - 1 do
		-- Spread rather than clustered, and offset in Z so a straight line
		-- through the middle is never the answer.
		local slot = math.floor(index * (slots / hazardCount))
		local z = if index % 2 == 0 then -4 else 4
		local hazard = makePart(
			context.model,
			Vector3.new(4, 4, 6),
			context.origin + Vector3.new(x + slot * step + step / 2, 2.5, z),
			COLOUR_HAZARD
		)
		hazard.CanCollide = false
		table.insert(context.hazards, hazard)
	end
	return length
end

export type BuiltCourse = {
	model: Model,
	checkpoints: { BasePart },
	animated: { Animated },
	spawnCFrame: CFrame,
	length: number,
}

local function buildCourse(spec: Types.ObstacleSpec, lane: number): BuiltCourse?
	local params = Obstacles.paramsForGrade(spec.grade)
	local origin = laneOrigin(lane)

	local model = Instance.new("Model")
	model.Name = `Course_{lane}`
	model.Parent = Workspace

	local context: BuildContext = {
		model = model,
		origin = origin,
		params = params,
		animated = {},
		hazards = {},
		tiles = {},
	}

	-- A landing pad to start on, so the first module is never a standing jump.
	local start = makePart(
		model,
		Vector3.new(20, PLATFORM_THICKNESS, PLATFORM_WIDTH),
		origin + Vector3.new(-10, 0, 0),
		COLOUR_CHECKPOINT
	)

	local checkpoints: { BasePart } = {}
	local x = 0
	for index, moduleId in spec.moduleIds do
		local builder = builders[moduleId]
		if builder == nil then
			model:Destroy()
			return nil
		end
		x += builder(context, x)

		local isLast = index == #spec.moduleIds
		local wantsCheckpoint = params.checkpointEvery > 0
			and index % params.checkpointEvery == 0
		if wantsCheckpoint or isLast then
			local pad = makePart(
				model,
				Vector3.new(10, PLATFORM_THICKNESS, PLATFORM_WIDTH),
				origin + Vector3.new(x + 5, 0, 0),
				COLOUR_CHECKPOINT
			)
			table.insert(checkpoints, pad)
			x += 10
		end
	end

	-- Dress the course by grade tier. A first-year course and a graduating-year
	-- course were the same grey before this: the difficulty curve was real but
	-- invisible, so a hard course read as an unfair one rather than a late one.
	-- The tint is a lerp rather than a replacement, because the colours also carry
	-- meaning -- red is a hazard at every grade, and a tier that overrode that
	-- would be dressing at the cost of readability.
	local tier = Decor.tierFor(spec.grade)
	-- Decor speaks packed integers so the tests can run it outside Roblox; the
	-- conversion happens once, here, at the boundary.
	local accent = Build.colour(tier.accent)
	for _, descendant in model:GetDescendants() do
		if descendant:IsA("BasePart") then
			descendant.Color = descendant.Color:Lerp(accent, 0.22)
		end
	end

	-- A gate at the start, carrying the grade. It is the only place the player is
	-- told what they are about to attempt.
	for _, side in { -1, 1 } do
		makePart(
			model,
			Vector3.new(2, 16, 2),
			origin + Vector3.new(-18, 8, side * (PLATFORM_WIDTH / 2)),
			accent
		)
	end
	local lintel = makePart(
		model,
		Vector3.new(2, 2, PLATFORM_WIDTH + 2),
		origin + Vector3.new(-18, 17, 0),
		accent
	)
	local gateSign = Instance.new("BillboardGui")
	gateSign.Size = UDim2.fromOffset(240, 56)
	gateSign.StudsOffsetWorldSpace = Vector3.new(0, 3, 0)
	gateSign.MaxDistance = 220
	gateSign.Parent = lintel
	local gateText = Instance.new("TextLabel")
	gateText.Size = UDim2.fromScale(1, 1)
	gateText.BackgroundTransparency = 1
	gateText.Font = Enum.Font.GothamBold
	gateText.TextSize = 30
	gateText.TextColor3 = Color3.fromRGB(255, 255, 255)
	gateText.TextStrokeTransparency = 0.35
	-- The grade as a bare numeral: the one label that needs no translation, on a
	-- part built once for a course every locale runs.
	gateText.Text = tostring(spec.grade)
	gateText.Parent = gateSign

	-- Tagged rather than returned, so wiring can walk the finished model once
	-- instead of threading two more lists through every builder.
	for _, hazard in context.hazards do
		hazard:AddTag("CourseHazard")
	end
	for _, tile in context.tiles do
		tile:AddTag("CourseTile")
	end

	return {
		model = model,
		checkpoints = checkpoints,
		animated = context.animated,
		spawnCFrame = CFrame.new(start.Position + Vector3.new(0, 4, 0)),
		length = x,
	}
end

local function stepRun(run: Run, delta: number)
	for _, item in run.animated do
		item.phase += delta * item.speed
		if item.kind == "slide" then
			local offset = math.sin(item.phase / math.max(item.range, 1)) * item.range
			local previous = item.part.Position
			local target = item.origin + Vector3.new(0, 0, offset)
			item.part.Position = target

			-- An anchored part moved by CFrame does not carry anyone standing
			-- on it, so riders are moved by the same delta explicitly.
			local shift = target - previous
			local character = run.player.Character
			local root = if character ~= nil
				then character:FindFirstChild("HumanoidRootPart")
				else nil
			if root ~= nil and root:IsA("BasePart") then
				local relative = root.Position - target
				if
					math.abs(relative.X) <= 8
					and math.abs(relative.Z) <= 8
					and relative.Y > 0
					and relative.Y < 8
				then
					root.CFrame = root.CFrame + shift
				end
			end
		else
			item.part.CFrame = CFrame.new(item.origin)
				* CFrame.Angles(0, item.phase, 0)
		end
	end
end

local function cleanup(run: Run)
	run.finished = true
	runs[run.player] = nil
	lanesInUse[run.lane] = nil
	run.model:Destroy()
end

local function report(run: Run, event: string, extra: { [string]: any }?)
	local payload: { [string]: any } = extra or {}
	payload.event = event
	payload.reached = run.reached
	payload.total = #run.checkpoints
	Remotes.event(Remotes.Names.CourseState):FireClient(run.player, payload)
end

local function respawnAtCheckpoint(run: Run)
	local character = run.player.Character
	local root = if character ~= nil then character:FindFirstChild("HumanoidRootPart") else nil
	if root ~= nil and root:IsA("BasePart") then
		root.CFrame = run.lastCheckpointCFrame
		root.AssemblyLinearVelocity = Vector3.zero
	end
	run.legStartedAt = os.clock()
end

local function finish(run: Run, passed: boolean, reason: string?)
	if run.finished then
		return
	end
	-- Claimed before settling, not after. Settling yields -- checking a game pass
	-- is a web call -- and during that yield another checkpoint touch or the
	-- heartbeat's time-limit check walks straight back in here and pays the run
	-- out a second time.
	run.finished = true
	runs[run.player] = nil

	local total = #run.checkpoints
	local summary = RewardService.settle(run.player, {
		subject = run.subject,
		statKey = run.statKey,
		passed = passed,
		score = run.reached,
		total = total,
		teacherUserId = run.teacherUserId,
		classMembers = run.classMembers,
		teacherRating = run.teacherRating,
		translated = run.translated,
		elapsedSeconds = os.clock() - run.startedAt,
		-- A course a student is expected to finish in about two thirds of its
		-- limit; the limit itself is the point of failure, not the target.
		expectedSeconds = run.params.timeLimitSeconds * 0.6,
	})

	local player = run.player
	cleanup(run)

	Remotes.event(Remotes.Names.CourseFinished):FireClient(player, {
		passed = passed,
		reason = reason,
		reached = summary ~= nil and summary.score or 0,
		total = total,
		pointsAwarded = if summary ~= nil then summary.pointsAwarded else 0,
		grade = if summary ~= nil then summary.grade else 0,
		advanced = summary ~= nil and summary.advanced or false,
		graduated = summary ~= nil and summary.graduated or false,
	})
end

--- A fall, a hazard, or a spinner. With checkpoints the student restarts the leg;
--- without them -- which is grades ten and eleven -- the run is simply over.
local function failLeg(run: Run, reason: string)
	if run.finished then
		return
	end
	if run.params.checkpointEvery == 0 then
		finish(run, false, reason)
		return
	end
	respawnAtCheckpoint(run)
	report(run, "reset", { reason = reason })
end

local function onCheckpoint(run: Run, index: number, pad: BasePart)
	if run.finished or index ~= run.reached + 1 then
		-- Out of order means either a genuine skip or a teleport. Either way it
		-- does not count, and the student has to come back for it.
		return
	end

	-- Time floor for the leg just covered. A character runs at sixteen studs a
	-- second; anything that covered this distance faster than forty did not run.
	local elapsed = os.clock() - run.legStartedAt
	local floor = run.legLength / IMPLAUSIBLE_SPEED
	if elapsed < floor then
		finish(run, false, "impossibleSpeed")
		return
	end

	run.reached = index
	run.lastCheckpointCFrame = CFrame.new(pad.Position + Vector3.new(0, 4, 0))
	run.legStartedAt = os.clock()

	local nextPad = run.checkpoints[index + 1]
	run.legLength = if nextPad ~= nil
		then (nextPad.Position - pad.Position).Magnitude
		else 0

	if index >= #run.checkpoints then
		finish(run, true, nil)
	else
		report(run, "checkpoint")
	end
end

local function characterRoot(player: Player): BasePart?
	local character = player.Character
	if character == nil then
		return nil
	end
	local root = character:FindFirstChild("HumanoidRootPart")
	return if root ~= nil and root:IsA("BasePart") then root else nil
end

local function wireTouches(run: Run, built: BuiltCourse)
	for index, pad in built.checkpoints do
		pad.Touched:Connect(function(hit: BasePart)
			local character = hit.Parent
			if character ~= nil and Players:GetPlayerFromCharacter(character) == run.player then
				onCheckpoint(run, index, pad)
			end
		end)
	end

	for _, hazard in run.model:GetDescendants() do
		if not hazard:IsA("BasePart") then
			continue
		end
		if hazard:HasTag("CourseHazard") then
			hazard.Touched:Connect(function(hit: BasePart)
				local character = hit.Parent
				if character ~= nil and Players:GetPlayerFromCharacter(character) == run.player then
					failLeg(run, "hazard")
				end
			end)
		elseif hazard:HasTag("CourseTile") then
			local triggered = false
			hazard.Touched:Connect(function(hit: BasePart)
				if triggered then
					return
				end
				local character = hit.Parent
				if character == nil or Players:GetPlayerFromCharacter(character) ~= run.player then
					return
				end
				triggered = true
				task.delay(run.params.vanishSeconds, function()
					if hazard.Parent == nil then
						return
					end
					hazard.CanCollide = false
					hazard.Transparency = 1
				end)
			end)
		end
	end
end

--- Starts a course. Returns a reason when it cannot begin, so the caller can tell
--- the student why rather than leaving them looking at nothing.
function ObstacleService.begin(
	player: Player,
	class: Types.Class,
	lesson: Types.Lesson
): string?
	if runs[player] ~= nil then
		return "alreadyRunning"
	end
	local spec = lesson.obstacle
	if spec == nil then
		return "notACourse"
	end

	local lane = takeLane()
	if lane == nil then
		return "noLane"
	end

	local built = buildCourse(spec, lane)
	if built == nil then
		lanesInUse[lane] = nil
		return "buildFailed"
	end
	if #built.checkpoints == 0 then
		built.model:Destroy()
		lanesInUse[lane] = nil
		return "buildFailed"
	end

	local root = characterRoot(player)
	if root == nil then
		built.model:Destroy()
		lanesInUse[lane] = nil
		return "noCharacter"
	end

	local params = Obstacles.paramsForGrade(spec.grade)
	local run: Run = {
		player = player,
		lane = lane,
		model = built.model,
		subject = class.subject,
		statKey = lesson.id,
		teacherUserId = class.teacherUserId,
		classMembers = ClassService.liveMembers(class),
		teacherRating = class.rating,
		-- A course has no text in it, so there is no translated version of it
		-- for anyone to complete and no reach share to pay.
		translated = false,
		params = params,
		checkpoints = built.checkpoints,
		reached = 0,
		lastCheckpointCFrame = built.spawnCFrame,
		startedAt = os.clock(),
		legStartedAt = os.clock(),
		legLength = (built.checkpoints[1].Position - built.spawnCFrame.Position).Magnitude,
		minX = laneOrigin(lane).X - BOUNDS_MARGIN,
		maxX = laneOrigin(lane).X + built.length + BOUNDS_MARGIN,
		maxZ = BOUNDS_MARGIN,
		ceilingY = laneOrigin(lane).Y + CEILING_HEIGHT,
		lastPosition = nil,
		animated = built.animated,
		finished = false,
	}

	runs[player] = run
	wireTouches(run, built)
	root.CFrame = built.spawnCFrame
	root.AssemblyLinearVelocity = Vector3.zero

	Remotes.event(Remotes.Names.CourseState):FireClient(player, {
		event = "start",
		title = lesson.title,
		grade = spec.grade,
		reached = 0,
		total = #built.checkpoints,
		timeLimitSeconds = params.timeLimitSeconds,
	})
	return nil
end

function ObstacleService.abandon(player: Player)
	local run = runs[player]
	if run ~= nil then
		cleanup(run)
	end
end

function ObstacleService.start()
	if heartbeat ~= nil then
		return
	end
	heartbeat = RunService.Heartbeat:Connect(function(delta: number)
		-- Snapshotted, because settling a run yields and another run can start or
		-- end during that yield -- mutating the table this loop is walking.
		local active: { Run } = {}
		for _, run in runs do
			table.insert(active, run)
		end

		for _, run in active do
			if run.finished then
				continue
			end
			stepRun(run, delta)

			if os.clock() - run.startedAt > run.params.timeLimitSeconds then
				finish(run, false, "timeLimit")
				continue
			end

			local root = characterRoot(run.player)
			if root == nil then
				continue
			end

			local origin = laneOrigin(run.lane)
			local position = root.Position

			if position.Y < origin.Y - FALL_DISTANCE then
				failLeg(run, "fell")
				continue
			end

			-- Over the top of the course rather than along it, or off the side of
			-- the lane entirely. A checkpoint order check cannot see this: a flier
			-- still touches every pad, in order.
			local offLane = position.X < run.minX
				or position.X > run.maxX
				or math.abs(position.Z - origin.Z) > run.maxZ
			if offLane or position.Y > run.ceilingY then
				finish(run, false, "impossibleSpeed")
				continue
			end

			-- Horizontal only. Falling accelerates and would trip a check that
			-- counted vertical distance, and falling is already handled above.
			local previous = run.lastPosition
			run.lastPosition = position
			if previous ~= nil and delta > 0 then
				local moved = (Vector3.new(position.X, 0, position.Z)
					- Vector3.new(previous.X, 0, previous.Z)).Magnitude
				if moved / delta > IMPLAUSIBLE_FRAME_SPEED then
					finish(run, false, "impossibleSpeed")
				end
			end
		end
	end)

	Players.PlayerRemoving:Connect(ObstacleService.abandon)
end

return ObstacleService
