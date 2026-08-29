--!strict
--- The rooms, and what is in them.
---
--- A classroom is one function taking a theme, because the difference between
--- the maths room and the history room is data, not code. What is not data is the
--- props: a lab needs beakers and a gym needs a vaulting horse, and no amount of
--- palette makes a cube read as either. So `props` in the theme says how many,
--- and this file says what.
---
--- Facing is +1 or -1: which side of the corridor the room sits on. Every offset
--- multiplies by it, so one function builds both sides and the two never drift.

local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Decor = require(ReplicatedStorage.Shared.Config.Decor)
local Build = require(script.Parent.Build)

local Rooms = {}

Rooms.Width = 34
Rooms.Depth = 30
Rooms.WallHeight = 14
Rooms.WallThickness = 1
Rooms.CorridorWidth = 24

local DOOR_WIDTH = 8

--- One conversion per room, at the top of the function that builds it.
---
--- Config speaks packed 0xRRGGBB integers and material names so the unit tests
--- can execute it outside Roblox; everything below this line speaks Color3 and
--- Enum.Material, and the two never mix in the same expression.
local function palette(theme: Decor.Theme): Palette
	return {
		wall = Build.colour(theme.wall),
		trim = Build.colour(theme.trim),
		board = Build.colour(theme.board),
		floor = Build.colour(theme.floor),
		floorMaterial = Build.material(theme.floorMaterial),
		light = Build.colour(theme.light),
		lightBrightness = theme.lightBrightness,
		effect = theme.effect,
		effectColour = Build.colour(theme.effectColour),
		props = theme.props,
	}
end

export type Room = {
	model: Model,
	skin: Palette,
	--- Where a teacher stands, and where the front of the room is.
	front: Vector3,
	centre: Vector3,
	facing: number,
	--- Only the assembly hall has one. It is where the director stands, and the
	--- caller needs it to put a podium prompt there.
	stage: BasePart?,
}

--- Walls, floor, ceiling, windows and the light. Everything a room has before
--- anyone decides what is taught in it.
local function shell(parent: Instance, name: string, centre: Vector3, skin: Palette, facing: number, width: number, depth: number): Model
	local room = Instance.new("Model")
	room.Name = name
	room.Parent = parent

	Build.block(room, "Floor", Vector3.new(width, 1, depth), centre, skin.floor, {
		material = skin.floorMaterial,
	})

	local ceilingY = centre.Y + Rooms.WallHeight
	Build.block(
		room,
		"Ceiling",
		Vector3.new(width, 0.6, depth),
		Vector3.new(centre.X, ceilingY, centre.Z),
		skin.wall,
		{ castShadow = false }
	)

	-- The far wall, with windows punched into it: two panes and the piers
	-- between them, rather than a glass wall, so the building has weight.
	local backZ = centre.Z + facing * (depth / 2)
	local pier = width / 5
	for slot = -2, 2 do
		local x = centre.X + slot * pier
		local isWindow = slot == -1 or slot == 1
		if isWindow then
			Build.block(
				room,
				"Sill",
				Vector3.new(pier, 4, Rooms.WallThickness),
				Vector3.new(x, centre.Y + 2, backZ),
				skin.wall
			)
			Build.window(
				room,
				"Pane",
				Vector3.new(pier - 1, 6, Rooms.WallThickness * 0.6),
				Vector3.new(x, centre.Y + 7, backZ)
			)
			Build.block(
				room,
				"Lintel",
				Vector3.new(pier, Rooms.WallHeight - 10, Rooms.WallThickness),
				Vector3.new(x, centre.Y + 10 + (Rooms.WallHeight - 10) / 2, backZ),
				skin.wall
			)
		else
			Build.block(
				room,
				"BackWall",
				Vector3.new(pier, Rooms.WallHeight, Rooms.WallThickness),
				Vector3.new(x, centre.Y + Rooms.WallHeight / 2, backZ),
				skin.wall
			)
		end
	end

	for _, side in { -1, 1 } do
		Build.block(
			room,
			"SideWall",
			Vector3.new(Rooms.WallThickness, Rooms.WallHeight, depth),
			Vector3.new(centre.X + side * (width / 2), centre.Y + Rooms.WallHeight / 2, centre.Z),
			skin.wall
		)
	end

	-- The corridor wall, with a doorway in the middle of it.
	local frontZ = centre.Z - facing * (depth / 2)
	local jamb = (width - DOOR_WIDTH) / 2
	for _, side in { -1, 1 } do
		Build.block(
			room,
			"FrontWall",
			Vector3.new(jamb, Rooms.WallHeight, Rooms.WallThickness),
			Vector3.new(
				centre.X + side * (DOOR_WIDTH / 2 + jamb / 2),
				centre.Y + Rooms.WallHeight / 2,
				frontZ
			),
			skin.wall
		)
	end
	Build.block(
		room,
		"DoorHead",
		Vector3.new(DOOR_WIDTH, Rooms.WallHeight - 9, Rooms.WallThickness),
		Vector3.new(centre.X, centre.Y + 9 + (Rooms.WallHeight - 9) / 2, frontZ),
		skin.trim
	)

	-- Trim under the ceiling: the one band of subject colour visible from the
	-- corridor, which is what makes eight rooms tell themselves apart at a glance.
	for _, side in { -1, 1 } do
		Build.block(
			room,
			"Trim",
			Vector3.new(width, 0.8, 0.3),
			Vector3.new(centre.X, ceilingY - 1.4, centre.Z + side * (depth / 2 - 0.6)),
			skin.trim,
			{ canCollide = false, castShadow = false }
		)
	end

	Build.lamp(
		room,
		Vector3.new(centre.X, ceilingY - 1, centre.Z),
		skin.light,
		skin.lightBrightness,
		42
	)

	return room
end

--- Desks in rows, angled slightly inward so the room has a focus.
local function seating(room: Model, centre: Vector3, skin: Palette, facing: number, rows: number)
	local backZ = centre.Z + facing * (Rooms.Depth / 2)
	for row = 1, rows do
		for seat = -1, 1 do
			local z = backZ - facing * (10 + row * 5)
			local x = centre.X + seat * 9
			-- Angled toward the board. Three degrees is not noticed directly and
			-- is very much noticed in aggregate: parallel rows read as a warehouse.
			local yaw = math.rad(-seat * 3 * facing)
			local cf = CFrame.new(Vector3.new(x, centre.Y + 2.6, z)) * CFrame.Angles(0, yaw, 0)
			Build.part(room, "Desk", Vector3.new(6, 0.4, 3), cf, skin.floor, {
				material = Enum.Material.WoodPlanks,
			})
			for _, leg in { -2.4, 2.4 } do
				Build.part(
					room,
					"DeskLeg",
					Vector3.new(0.3, 2.4, 0.3),
					cf * CFrame.new(leg, -1.4, 0),
					skin.trim,
					{ castShadow = false }
				)
			end
			Build.part(
				room,
				"Chair",
				Vector3.new(2.4, 0.3, 2.4),
				cf * CFrame.new(0, -0.9, facing * 2.6),
				skin.trim,
				{ material = Enum.Material.Wood }
			)
			Build.part(
				room,
				"ChairBack",
				Vector3.new(2.4, 2.2, 0.3),
				cf * CFrame.new(0, 0.2, facing * 3.7),
				skin.trim,
				{ material = Enum.Material.Wood }
			)
		end
	end
end

--- What sits on the shelf at the back. Each subject gets shapes that could only
--- be its own: flasks in the lab, a bust in literature, a pommel horse in the gym.
local function props(room: Model, centre: Vector3, skin: Palette, facing: number, subject: string)
	local backZ = centre.Z + facing * (Rooms.Depth / 2)
	local shelfZ = backZ - facing * 2.2
	local count = skin.props

	local function at(index: number): Vector3
		-- Spread across the back wall, avoiding the middle where the board is.
		local span = Rooms.Width - 8
		local t = if count <= 1 then 0.5 else (index - 1) / (count - 1)
		return Vector3.new(centre.X - span / 2 + t * span, centre.Y + 1.5, shelfZ)
	end

	if subject == "science" then
		Build.block(
			room,
			"Bench",
			Vector3.new(Rooms.Width - 10, 0.5, 3),
			Vector3.new(centre.X, centre.Y + 3.1, shelfZ),
			skin.trim,
			{ material = Enum.Material.Metal }
		)
		for i = 1, count do
			local base = at(i) + Vector3.new(0, 2.4, 0)
			Build.block(room, "Flask", Vector3.new(1, 1.6, 1), base, skin.effectColour, {
				material = Enum.Material.Glass,
				transparency = 0.4,
				castShadow = false,
			})
			Build.block(room, "FlaskNeck", Vector3.new(0.4, 0.8, 0.4), base + Vector3.new(0, 1.2, 0), skin.effectColour, {
				material = Enum.Material.Glass,
				transparency = 0.4,
				castShadow = false,
			})
		end
	elseif subject == "art" then
		for i = 1, count do
			local base = at(i)
			-- An easel: three legs and a canvas, each one a different colour so
			-- the back of the room looks like work in progress.
			local hue = (i - 1) / math.max(1, count)
			local canvas = Color3.fromHSV(hue, 0.5, 0.95)
			Build.part(room, "EaselLeg", Vector3.new(0.3, 5, 0.3), CFrame.new(base + Vector3.new(0, 2, 0)) * CFrame.Angles(math.rad(facing * 8), 0, 0), skin.trim)
			Build.block(room, "Canvas", Vector3.new(3.2, 3.2, 0.2), base + Vector3.new(0, 4.4, -facing * 0.4), canvas, { castShadow = false })
		end
	elseif subject == "literature" or subject == "history" or subject == "language" then
		for i = 1, count do
			local base = at(i)
			Build.block(room, "Shelf", Vector3.new(4.4, 6, 1.6), base + Vector3.new(0, 3, 0), skin.trim, {
				material = Enum.Material.Wood,
			})
			for shelfRow = 1, 3 do
				Build.block(
					room,
					"Books",
					Vector3.new(3.8, 1.2, 1.1),
					base + Vector3.new(0, shelfRow * 1.7, 0),
					Color3.fromHSV(((i * 3 + shelfRow) % 7) / 7, 0.42, 0.68),
					{ castShadow = false }
				)
			end
		end
	elseif subject == "pe" then
		for i = 1, count do
			local base = at(i)
			Build.block(room, "Horse", Vector3.new(6, 1.6, 2.6), base + Vector3.new(0, 3.4, 0), skin.trim, {
				material = Enum.Material.Fabric,
			})
			for _, leg in { -2.2, 2.2 } do
				Build.block(room, "HorseLeg", Vector3.new(0.4, 2.8, 0.4), base + Vector3.new(leg, 1.4, 0), skin.floor)
			end
		end
	elseif subject == "logic" then
		for i = 1, count do
			local base = at(i)
			-- A stack of cubes, rotated a little more each time. Reads as a
			-- puzzle mid-solve, which is the whole subject in one prop.
			for level = 1, 3 do
				Build.part(
					room,
					"Block",
					Vector3.new(1.6, 1.6, 1.6),
					CFrame.new(base + Vector3.new(0, level * 1.7, 0))
						* CFrame.Angles(0, math.rad(level * 14 + i * 20), 0),
					if level == 2 then skin.trim else skin.effectColour,
					{ material = Enum.Material.Neon, castShadow = false }
				)
			end
		end
	else
		for i = 1, count do
			local base = at(i)
			Build.block(room, "Cabinet", Vector3.new(3.4, 5, 1.8), base + Vector3.new(0, 2.5, 0), skin.trim, {
				material = Enum.Material.Wood,
			})
		end
	end
end

--- A classroom: shell, board, teacher's desk, seating, props and the effect.
--- Returns where the teacher stands so the caller can put one there without
--- knowing the room's internal geometry.
function Rooms.classroom(
	parent: Instance,
	centre: Vector3,
	subject: string,
	facing: number,
	labelKey: string
): Room
	local skin = palette(Decor.forSubject(subject))
	local room = shell(parent, `Room_{subject}`, centre, skin, facing, Rooms.Width, Rooms.Depth)
	local backZ = centre.Z + facing * (Rooms.Depth / 2)

	local board = Build.block(
		room,
		"Board",
		Vector3.new(Rooms.Width * 0.55, 7, 0.4),
		Vector3.new(centre.X, centre.Y + 6.5, backZ - facing * 0.9),
		skin.board,
		{ material = Enum.Material.Slate, castShadow = false }
	)
	Build.block(
		room,
		"BoardFrame",
		Vector3.new(Rooms.Width * 0.55 + 1, 8, 0.2),
		Vector3.new(centre.X, centre.Y + 6.5, backZ - facing * 1.2),
		skin.trim,
		{ canCollide = false, castShadow = false }
	)

	Build.block(
		room,
		"TeacherDesk",
		Vector3.new(9, 0.5, 3.4),
		Vector3.new(centre.X, centre.Y + 3, backZ - facing * 6),
		skin.trim,
		{ material = Enum.Material.Wood }
	)
	Build.block(
		room,
		"TeacherDeskBody",
		Vector3.new(8.4, 2.6, 3),
		Vector3.new(centre.X, centre.Y + 1.7, backZ - facing * 6),
		skin.floor,
		{ material = Enum.Material.Wood }
	)

	seating(room, centre, skin, facing, 3)
	props(room, centre, skin, facing, subject)

	-- The effect hangs in the middle of the room rather than at the board, so it
	-- reads as atmosphere rather than as something the board is doing.
	local emission = Decor.Emissions[skin.effect]
	if emission ~= nil then
		local anchor = Build.block(
			room,
			"EffectAnchor",
			Vector3.new(Rooms.Width - 6, 0.2, Rooms.Depth - 6),
			Vector3.new(centre.X, centre.Y + 8, centre.Z),
			skin.effectColour,
			{ transparency = 1, canCollide = false, castShadow = false }
		)
		Build.emitter(anchor, skin.effect, emission, skin.effectColour)
	end

	-- The door sign, facing the corridor, which is the only label a player sees
	-- before deciding whether to walk in.
	local frontZ = centre.Z - facing * (Rooms.Depth / 2)
	local plate = Build.block(
		room,
		"DoorSign",
		Vector3.new(DOOR_WIDTH, 1.4, 0.3),
		Vector3.new(centre.X, centre.Y + 10.4, frontZ - facing * 0.7),
		skin.trim,
		{ canCollide = false, castShadow = false }
	)
	Build.signKey(plate, labelKey, 1.6, Color3.fromRGB(255, 255, 255), 20)
	Build.signKey(board, labelKey, 4.6, Color3.fromRGB(240, 244, 250), 22)

	return {
		model = room,
		palette = skin,
		front = Vector3.new(centre.X, centre.Y + 0.5, backZ - facing * 9),
		centre = centre,
		facing = facing,
	}
end

--- The gym. Wider and taller than a classroom, no desks, and a marked-out floor
--- so it reads as a hall rather than a big empty room.
function Rooms.gym(parent: Instance, centre: Vector3, facing: number, labelKey: string): Room
	local skin = palette(Decor.forHall("gym"))
	local width, depth = Rooms.Width * 2, Rooms.Depth * 1.6
	local room = shell(parent, "Hall_gym", centre, skin, facing, width, depth)

	-- Court lines. Two circles' worth of markings would need meshes; a centre
	-- line and a key at each end says "sports hall" with four boxes.
	Build.block(room, "CentreLine", Vector3.new(width - 4, 0.05, 0.6), Vector3.new(centre.X, centre.Y + 0.55, centre.Z), Color3.fromRGB(236, 232, 220), { canCollide = false, castShadow = false })
	for _, side in { -1, 1 } do
		Build.block(room, "Key", Vector3.new(14, 0.05, 0.6), Vector3.new(centre.X, centre.Y + 0.55, centre.Z + side * depth / 4), Color3.fromRGB(236, 232, 220), { canCollide = false, castShadow = false })
	end

	-- Wall bars down both long sides.
	for _, side in { -1, 1 } do
		for bar = 1, 9 do
			Build.block(
				room,
				"WallBar",
				Vector3.new(0.4, 0.4, 10),
				Vector3.new(centre.X + side * (width / 2 - 1), centre.Y + 1 + bar * 1.1, centre.Z),
				skin.trim,
				{ material = Enum.Material.Wood, castShadow = false }
			)
		end
	end

	local backZ = centre.Z + facing * (depth / 2)
	local scoreboard = Build.block(
		room,
		"Scoreboard",
		Vector3.new(16, 6, 0.5),
		Vector3.new(centre.X, centre.Y + 10, backZ - facing * 0.9),
		skin.board,
		{ material = Enum.Material.Metal, castShadow = false }
	)
	Build.signKey(scoreboard, labelKey, 4, Color3.fromRGB(255, 236, 210), 26)

	local emission = Decor.Emissions[skin.effect]
	if emission ~= nil then
		local anchor = Build.block(room, "EffectAnchor", Vector3.new(width - 8, 0.2, depth - 8), Vector3.new(centre.X, centre.Y + 9, centre.Z), skin.effectColour, { transparency = 1, canCollide = false, castShadow = false })
		Build.emitter(anchor, skin.effect, emission, skin.effectColour)
	end

	return {
		model = room,
		palette = skin,
		front = Vector3.new(centre.X, centre.Y + 0.5, backZ - facing * 8),
		centre = centre,
		facing = facing,
	}
end

--- The library. Stacks in rows you can walk between, low warm light, dust.
function Rooms.library(parent: Instance, centre: Vector3, facing: number, labelKey: string): Room
	local skin = palette(Decor.forHall("library"))
	local width, depth = Rooms.Width * 1.5, Rooms.Depth * 1.4
	local room = shell(parent, "Hall_library", centre, skin, facing, width, depth)

	for column = -1, 1 do
		for row = -1, 1 do
			local base = Vector3.new(centre.X + column * 14, centre.Y + 4, centre.Z + row * 12)
			Build.block(room, "Stack", Vector3.new(3, 8, 9), base, skin.trim, { material = Enum.Material.Wood })
			for shelfRow = 1, 4 do
				for _, side in { -1, 1 } do
					Build.block(
						room,
						"Books",
						Vector3.new(0.6, 1.4, 8),
						base + Vector3.new(side * 1.6, -3 + shelfRow * 1.7, 0),
						Color3.fromHSV(((column + 2) * 3 + row + shelfRow) % 8 / 8, 0.38, 0.6),
						{ canCollide = false, castShadow = false }
					)
				end
			end
		end
	end

	local backZ = centre.Z + facing * (depth / 2)
	local plate = Build.block(room, "LibrarySign", Vector3.new(12, 1.6, 0.4), Vector3.new(centre.X, centre.Y + 11, backZ - facing * 0.8), skin.trim, { canCollide = false, castShadow = false })
	Build.signKey(plate, labelKey, 1.8, Color3.fromRGB(255, 240, 214), 24)

	local emission = Decor.Emissions[skin.effect]
	if emission ~= nil then
		local anchor = Build.block(room, "EffectAnchor", Vector3.new(width - 6, 0.2, depth - 6), Vector3.new(centre.X, centre.Y + 9, centre.Z), skin.effectColour, { transparency = 1, canCollide = false, castShadow = false })
		Build.emitter(anchor, skin.effect, emission, skin.effectColour)
	end

	return { model = room, palette = skin, front = Vector3.new(centre.X, centre.Y + 0.5, backZ - facing * 7), centre = centre, facing = facing }
end

--- The assembly hall: a raked floor of seats facing a stage. This is where the
--- director stands, so it is the one room whose geometry is about one person
--- being visible from everywhere in it.
function Rooms.assembly(parent: Instance, centre: Vector3, facing: number, labelKey: string): Room
	local skin = palette(Decor.forHall("assembly"))
	local width, depth = Rooms.Width * 2.2, Rooms.Depth * 1.8
	local room = shell(parent, "Hall_assembly", centre, skin, facing, width, depth)

	local backZ = centre.Z + facing * (depth / 2)

	local stage = Build.block(
		room,
		"Stage",
		Vector3.new(width - 10, 3, 16),
		Vector3.new(centre.X, centre.Y + 2, backZ - facing * 9),
		skin.trim,
		{ material = Enum.Material.WoodPlanks, castShadow = true }
	)
	Build.stairs(
		room,
		"StageStep",
		Vector3.new(centre.X, centre.Y + 0.5, backZ - facing * 17.5) - Vector3.new(0, 0, facing * 1.5),
		3,
		1,
		1.4,
		10,
		skin.trim
	)

	-- A curtain either side, and a backdrop. Fabric material sells it more than
	-- the geometry does.
	for _, side in { -1, 1 } do
		Build.block(
			room,
			"Curtain",
			Vector3.new(6, 12, 1),
			Vector3.new(centre.X + side * (width / 2 - 7), centre.Y + 8, backZ - facing * 2),
			skin.board,
			{ material = Enum.Material.Fabric, castShadow = false }
		)
	end
	Build.block(
		room,
		"Backdrop",
		Vector3.new(width - 20, 12, 0.4),
		Vector3.new(centre.X, centre.Y + 8, backZ - facing * 1.4),
		skin.board,
		{ material = Enum.Material.Fabric, castShadow = false }
	)

	local podium = Build.block(
		room,
		"Podium",
		Vector3.new(4, 4, 2.6),
		Vector3.new(centre.X, centre.Y + 5.5, backZ - facing * 6),
		skin.floor,
		{ material = Enum.Material.Wood }
	)
	Build.signKey(podium, labelKey, 3.6, Color3.fromRGB(255, 232, 226), 26)

	-- Raked rows: each row further back sits a little higher, which is what makes
	-- a hall of a hundred people work as a room rather than a queue.
	for row = 1, 6 do
		local rise = row * 0.7
		local z = backZ - facing * (22 + row * 6)
		Build.block(
			room,
			"Riser",
			Vector3.new(width - 8, rise, 6),
			Vector3.new(centre.X, centre.Y + rise / 2, z),
			skin.floor,
			{ material = Enum.Material.Concrete }
		)
		for seat = -4, 4 do
			Build.block(
				room,
				"Seat",
				Vector3.new(2.6, 0.4, 2.4),
				Vector3.new(centre.X + seat * 5, centre.Y + rise + 1.6, z),
				skin.trim,
				{ material = Enum.Material.Fabric, castShadow = false }
			)
			Build.block(
				room,
				"SeatBack",
				Vector3.new(2.6, 2.4, 0.3),
				Vector3.new(centre.X + seat * 5, centre.Y + rise + 2.6, z + facing * 1.2),
				skin.trim,
				{ material = Enum.Material.Fabric, castShadow = false }
			)
		end
	end

	-- Stage lights. The only place in the school with coloured light on purpose.
	for _, side in { -2, 0, 2 } do
		Build.lamp(
			room,
			Vector3.new(centre.X + side * 12, centre.Y + Rooms.WallHeight - 2, backZ - facing * 12),
			skin.light,
			2.4,
			36
		)
	end

	return {
		model = room,
		palette = skin,
		front = Vector3.new(centre.X, centre.Y + 3.5, backZ - facing * 8),
		centre = centre,
		facing = facing,
		stage = stage,
	}
end

--- The staff room, where the deans work. Small, carpeted, and the only room with
--- a table people sit around rather than rows facing a board.
function Rooms.staffroom(parent: Instance, centre: Vector3, facing: number, labelKey: string): Room
	local skin = palette(Decor.forHall("staffroom"))
	local width, depth = Rooms.Width, Rooms.Depth * 0.8
	local room = shell(parent, "Hall_staffroom", centre, skin, facing, width, depth)

	local table_ = Build.block(room, "Table", Vector3.new(16, 0.6, 7), Vector3.new(centre.X, centre.Y + 3, centre.Z), skin.trim, { material = Enum.Material.Wood })
	for _, side in { -1, 1 } do
		for seat = -2, 2 do
			Build.block(
				room,
				"Chair",
				Vector3.new(2.4, 0.4, 2.4),
				Vector3.new(centre.X + seat * 4, centre.Y + 2, centre.Z + side * 6),
				skin.floor,
				{ material = Enum.Material.Fabric, castShadow = false }
			)
		end
	end

	local backZ = centre.Z + facing * (depth / 2)
	local noticeboard = Build.block(
		room,
		"Noticeboard",
		Vector3.new(14, 6, 0.4),
		Vector3.new(centre.X, centre.Y + 7, backZ - facing * 0.8),
		skin.board,
		{ material = Enum.Material.Fabric, castShadow = false }
	)
	Build.signKey(noticeboard, labelKey, 4, Color3.fromRGB(232, 238, 250), 22)
	Build.signKey(table_, labelKey, 2.4, Color3.fromRGB(200, 206, 220), 16)

	return { model = room, palette = skin, front = Vector3.new(centre.X, centre.Y + 0.5, backZ - facing * 5), centre = centre, facing = facing }
end

return Rooms
