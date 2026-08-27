--!strict
--- The building seen from outside, and the ground it stands on.
---
--- This exists because of what a player sees in their first four seconds. They
--- spawn, and either there is a school in front of them or there is a floating
--- corridor on a baseplate. The corridor was the whole world before this file.
---
--- The corridor runs along X, so the front door is at the -X end of it: you come
--- up the steps, through the portico, and the corridor is straight ahead with
--- every classroom off it. Putting the entrance on a long side would have meant
--- arriving in the middle of the school facing a wall.
---
--- Nothing here is walked through except the steps and the doorway, so almost
--- all of it is CanCollide false. A facade you can get stuck inside is worse
--- than no facade.

local Build = require(script.Parent.Build)

local Exterior = {}

local BRICK = Color3.fromRGB(178, 128, 106)
local STONE = Color3.fromRGB(222, 216, 204)
local ROOF = Color3.fromRGB(84, 74, 78)
local GRASS = Color3.fromRGB(118, 154, 96)
local PATH = Color3.fromRGB(198, 192, 180)
local TRUNK = Color3.fromRGB(112, 82, 58)
local LEAF = Color3.fromRGB(96, 142, 84)

--- The school's floors sit at y = 0. The grounds sit below that, so the building
--- stands on a plinth you climb rather than on the same plane as the grass --
--- which is the difference between a school and a shed.
Exterior.GroundY = -6
Exterior.StepCount = 5
Exterior.StepRise = 1.3

export type Bounds = { minX: number, maxX: number, minZ: number, maxZ: number }

--- Where a player should arrive: on the path, outside the doors, facing them.
function Exterior.spawnPosition(bounds: Bounds): Vector3
	return Vector3.new(bounds.minX - 34, Exterior.GroundY + 1, (bounds.minZ + bounds.maxZ) / 2)
end

--- Grass, the approach path, a railing and some trees.
function Exterior.grounds(parent: Instance, bounds: Bounds)
	local centreZ = (bounds.minZ + bounds.maxZ) / 2
	local width = (bounds.maxX - bounds.minX) + 150
	local depth = (bounds.maxZ - bounds.minZ) + 90
	local centreX = (bounds.minX + bounds.maxX) / 2 - 30

	Build.block(
		parent,
		"Grounds",
		Vector3.new(width, 4, depth),
		Vector3.new(centreX, Exterior.GroundY - 2, centreZ),
		GRASS,
		{ material = Enum.Material.Grass }
	)

	-- The path runs up to the steps along X, matching the way in.
	Build.block(
		parent,
		"Path",
		Vector3.new(60, 0.2, 20),
		Vector3.new(bounds.minX - 32, Exterior.GroundY + 0.1, centreZ),
		PATH,
		{ material = Enum.Material.Concrete, castShadow = false }
	)

	-- Trees either side of the path rather than scattered: they frame the
	-- approach, which is the one view every player gets on every join.
	for _, side in { -1, 1 } do
		for row = 0, 3 do
			local base = Vector3.new(
				bounds.minX - 58 + row * 15,
				Exterior.GroundY,
				centreZ + side * 22
			)
			Build.block(parent, "Trunk", Vector3.new(2, 11, 2), base + Vector3.new(0, 5.5, 0), TRUNK, {
				material = Enum.Material.Wood,
				castShadow = true,
			})
			Build.block(parent, "Canopy", Vector3.new(13, 10, 13), base + Vector3.new(0, 14, 0), LEAF, {
				material = Enum.Material.Grass,
				canCollide = false,
				castShadow = true,
			})
		end
	end

	-- A railing round the plot: posts, not a solid wall, so it does not read as
	-- a compound. Spacing is derived so the count follows the plot size.
	local spacing = 14
	for x = bounds.minX - 80, bounds.maxX + 60, spacing do
		for _, side in { -1, 1 } do
			Build.block(
				parent,
				"Post",
				Vector3.new(1, 5, 1),
				Vector3.new(x, Exterior.GroundY + 2.5, centreZ + side * depth / 2),
				STONE,
				{ castShadow = false }
			)
		end
	end
end

--- Brick walls round the whole footprint, windows on two storeys, a portico and
--- steps at the -X end, and a stepped roof.
---
--- The roof is stepped blocks rather than wedges on purpose. A wedge's slope
--- direction depends on its orientation in a way that cannot be checked without
--- opening Studio, and a roof that is inside out is the most visible possible
--- bug. Steps are unambiguous from the numbers alone.
function Exterior.facade(parent: Instance, bounds: Bounds, height: number, mottoKey: string)
	local centreX = (bounds.minX + bounds.maxX) / 2
	local centreZ = (bounds.minZ + bounds.maxZ) / 2
	local width = bounds.maxX - bounds.minX
	local depth = bounds.maxZ - bounds.minZ

	Build.block(
		parent,
		"Plinth",
		Vector3.new(width + 10, math.abs(Exterior.GroundY) + 1, depth + 10),
		Vector3.new(centreX, Exterior.GroundY / 2, centreZ),
		STONE,
		{ material = Enum.Material.Concrete }
	)

	-- Long walls.
	for _, side in { -1, 1 } do
		Build.block(
			parent,
			"SideFacade",
			Vector3.new(width, height, 2),
			Vector3.new(centreX, height / 2, centreZ + side * depth / 2),
			BRICK,
			{ material = Enum.Material.Brick, canCollide = false, castShadow = true }
		)
	end

	-- The far end, and the entrance end with a doorway cut out of it.
	Build.block(
		parent,
		"BackFacade",
		Vector3.new(2, height, depth),
		Vector3.new(bounds.maxX, height / 2, centreZ),
		BRICK,
		{ material = Enum.Material.Brick, canCollide = false, castShadow = true }
	)

	local doorway = 20
	local jamb = (depth - doorway) / 2
	for _, side in { -1, 1 } do
		Build.block(
			parent,
			"FrontFacade",
			Vector3.new(2, height, jamb),
			Vector3.new(bounds.minX, height / 2, centreZ + side * (doorway / 2 + jamb / 2)),
			BRICK,
			{ material = Enum.Material.Brick, canCollide = false, castShadow = true }
		)
	end
	Build.block(
		parent,
		"FrontLintel",
		Vector3.new(2, height - 14, doorway),
		Vector3.new(bounds.minX, 14 + (height - 14) / 2, centreZ),
		BRICK,
		{ material = Enum.Material.Brick, canCollide = false, castShadow = true }
	)

	-- Windows in a grid on the long walls, two storeys.
	for _, side in { -1, 1 } do
		for storey = 1, 2 do
			local bays = math.max(2, math.floor(width / 28))
			for bay = 0, bays - 1 do
				Build.window(
					parent,
					"FacadeWindow",
					Vector3.new(5, 5, 2.4),
					Vector3.new(
						bounds.minX + (bay + 0.5) * (width / bays),
						storey * (height / 3) - 1,
						centreZ + side * depth / 2
					)
				)
			end
		end
	end

	-- Portico: four columns, an architrave and a pediment carrying the motto.
	local porchX = bounds.minX - 8
	for _, zSide in { -1, 1 } do
		for _, offset in { 6, 13 } do
			Build.block(
				parent,
				"Column",
				Vector3.new(2.6, 16, 2.6),
				Vector3.new(porchX, 8, centreZ + zSide * offset),
				STONE,
				{ material = Enum.Material.Marble, castShadow = true }
			)
		end
	end
	Build.block(parent, "Architrave", Vector3.new(12, 2.4, 34), Vector3.new(porchX + 2, 17, centreZ), STONE, { material = Enum.Material.Marble, canCollide = false, castShadow = true })
	local pediment = Build.block(parent, "Pediment", Vector3.new(12, 5, 34), Vector3.new(porchX + 2, 20.6, centreZ), STONE, { material = Enum.Material.Marble, canCollide = false, castShadow = true })
	Build.signKey(pediment, mottoKey, 3.6, Color3.fromRGB(64, 58, 54), 28)

	-- Steps from the grass up to the door sill. The rise is chosen so the top
	-- step lands on the floor rather than near it: GroundY is negative, and the
	-- corridor's walking surface is at +0.5.
	Build.stairs(
		parent,
		"Step",
		Vector3.new(porchX - 4 - Exterior.StepCount * 1.8, Exterior.GroundY, centreZ),
		Exterior.StepCount,
		Exterior.StepRise,
		1.8,
		28,
		STONE,
		{ material = Enum.Material.Concrete }
	)

	-- A stepped roof: four courses, each inset, reading as a pitch without
	-- depending on which way a wedge happens to face.
	local courses = 4
	for course = 1, courses do
		local inset = course * (depth / (courses * 3))
		Build.block(
			parent,
			"Roof",
			Vector3.new(width + 8 - inset, 2.4, depth + 8 - inset * 2),
			Vector3.new(centreX, height + course * 2.2, centreZ),
			ROOF,
			{ material = Enum.Material.Slate, canCollide = false, castShadow = true }
		)
	end

	-- A clock tower over the entrance. Every school has one, and it is how a
	-- player finds their way back to the door from the far end of the grounds.
	local towerZ = centreZ
	local towerX = bounds.minX + 14
	Build.block(parent, "Tower", Vector3.new(14, 26, 14), Vector3.new(towerX, height + 8, towerZ), BRICK, { material = Enum.Material.Brick, canCollide = false, castShadow = true })
	local face = Build.block(parent, "ClockFace", Vector3.new(0.6, 9, 9), Vector3.new(towerX - 7.2, height + 14, towerZ), Color3.fromRGB(246, 242, 232), { material = Enum.Material.Marble, canCollide = false, castShadow = false })
	Build.part(parent, "ClockHandHour", Vector3.new(0.3, 3.2, 0.5), CFrame.new(Vector3.new(towerX - 7.6, height + 15.2, towerZ)), Color3.fromRGB(40, 40, 46), { canCollide = false, castShadow = false })
	Build.part(parent, "ClockHandMinute", Vector3.new(0.3, 4.6, 0.4), CFrame.new(Vector3.new(towerX - 7.6, height + 14, towerZ)) * CFrame.Angles(math.rad(115), 0, 0), Color3.fromRGB(40, 40, 46), { canCollide = false, castShadow = false })
	for cap = 1, 3 do
		Build.block(parent, "Spire", Vector3.new(14 - cap * 3.6, 2.6, 14 - cap * 3.6), Vector3.new(towerX, height + 21 + cap * 2.4, towerZ), ROOF, { material = Enum.Material.Slate, canCollide = false, castShadow = true })
	end

	return face
end

--- The flagpole and the noticeboard by the doors: the two things carrying live
--- campus state, put where a player walks past them anyway.
function Exterior.entranceFurniture(parent: Instance, bounds: Bounds): (BasePart, BasePart)
	local centreZ = (bounds.minZ + bounds.maxZ) / 2
	local x = bounds.minX - 26

	local pole = Build.block(parent, "Flagpole", Vector3.new(0.8, 30, 0.8), Vector3.new(x, Exterior.GroundY + 15, centreZ - 20), Color3.fromRGB(226, 226, 232), { material = Enum.Material.Metal, castShadow = true })
	Build.block(parent, "Flag", Vector3.new(0.2, 5, 8), Vector3.new(x, Exterior.GroundY + 27, centreZ - 15.6), Color3.fromRGB(70, 96, 190), { material = Enum.Material.Fabric, canCollide = false, castShadow = false })

	local boardX = x
	local board = Build.block(parent, "Noticeboard", Vector3.new(0.8, 7, 13), Vector3.new(boardX, Exterior.GroundY + 7, centreZ + 20), Color3.fromRGB(96, 72, 52), { material = Enum.Material.Wood, castShadow = true })
	for _, leg in { -5, 5 } do
		Build.block(parent, "BoardLeg", Vector3.new(0.8, 4, 0.8), Vector3.new(boardX, Exterior.GroundY + 2, centreZ + 20 + leg), Color3.fromRGB(96, 72, 52), { material = Enum.Material.Wood })
	end

	return pole, board
end

return Exterior
