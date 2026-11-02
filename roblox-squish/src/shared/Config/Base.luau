--!strict
--- Geometry of the map: the plaza, the ring of bases, and every part of a base.
---
--- Built as plain numbers so the layout can be checked outside Studio. A base is
--- described in its own local frame -- origin at the floor centre, +Z pointing at
--- the plaza -- and World/BaseBuilder only places those boxes. The tests walk the
--- same list and check what Studio would otherwise show the first time someone
--- presses Play: walls that meet at the corners with no gap and no overlap, a
--- door a character fits through, shelves clear of the walls and of each other,
--- walls too tall to jump, bases that do not touch, and a carry from the far
--- side of the map that fits inside the carry timeout.

local Base = {}

export type Vec = { number }

export type Box = {
	name: string,
	size: Vec,
	centre: Vec,
	--- Colour key; BaseBuilder maps it onto the pastel palette.
	colour: string,
	--- Solid parts block movement. Decorative ones are CanCollide off.
	solid: boolean,
}

-- Footprint. Floor top sits at y = 0.
Base.Half = 30
Base.WallThickness = 2
Base.WallHeight = 14
Base.DoorWidth = 14
Base.FloorThickness = 1

-- Character physics the layout has to respect. Roblox defaults: a character is
-- about 2 studs wide and 5 tall, and jumps 7.2 studs.
Base.CharacterWidth = 2
Base.JumpHeight = 7.2

-- Shelves: three rows of six pedestals.
Base.SlotRows = { -20, -10, 0 }
Base.SlotColumns = { -20, -12, -4, 4, 12, 20 }
Base.SlotSize = { 5, 2, 5 }
Base.SlotCount = 18

-- Where a thief has to bring a squish home, and where its owner spawns.
Base.HomePad = { centre = { 0, 0.1, 15 }, size = { 14, 0.2, 8 } }

-- The entrance path outside the door, with one trap slot per trap.
Base.PathLength = 16
Base.TrapSlotZ = { 34, 38, 42 }
Base.TrapSize = { 10, 0.4, 3 }

-- The ring.
Base.PlotCount = 6
Base.RingRadius = 120
Base.PlazaRadius = 40
--- The box machine at the centre of the plaza, as a cylinder footprint.
Base.MachineRadius = 14
Base.GroundRadius = 230

--- The parts of one base in its local frame.
function Base.parts(): { Box }
	local h = Base.Half
	local t = Base.WallThickness
	local wallY = Base.WallHeight / 2
	local doorHalf = Base.DoorWidth / 2
	local parts: { Box } = {}

	local function add(name: string, size: Vec, centre: Vec, colour: string, solid: boolean)
		table.insert(parts, { name = name, size = size, centre = centre, colour = colour, solid = solid })
	end

	add("Floor", { 2 * h, Base.FloorThickness, 2 * h }, { 0, -Base.FloorThickness / 2, 0 }, "floor", true)

	-- Back wall spans the full width; side walls butt against its inner face and
	-- run to the front edge; the two front segments fill between the side walls
	-- and the door. Every joint is end-to-face, so nothing overlaps.
	add("WallBack", { 2 * h, Base.WallHeight, t }, { 0, wallY, -h + t / 2 }, "wall", true)
	add("WallLeft", { t, Base.WallHeight, 2 * h - t }, { -h + t / 2, wallY, t / 2 }, "wall", true)
	add("WallRight", { t, Base.WallHeight, 2 * h - t }, { h - t / 2, wallY, t / 2 }, "wall", true)
	local frontWidth = (h - t) - doorHalf
	local frontX = doorHalf + frontWidth / 2
	add("WallFrontLeft", { frontWidth, Base.WallHeight, t }, { -frontX, wallY, h - t / 2 }, "wall", true)
	add("WallFrontRight", { frontWidth, Base.WallHeight, t }, { frontX, wallY, h - t / 2 }, "wall", true)

	-- The sign arch over the door rests on the front segments.
	add("SignArch", { Base.DoorWidth + 2 * t, 3, t }, { 0, Base.WallHeight + 1.5, h - t / 2 }, "accent", true)

	add("HomePad", Base.HomePad.size, Base.HomePad.centre, "home", false)

	add("Path", { Base.DoorWidth, Base.FloorThickness, Base.PathLength }, {
		0,
		-Base.FloorThickness / 2,
		h + Base.PathLength / 2,
	}, "path", true)

	for index, z in Base.TrapSlotZ do
		add(`TrapSlot{index}`, Base.TrapSize, { 0, Base.TrapSize[2] / 2, z }, "trap", false)
	end

	for slot, centre in Base.slotCentres() do
		add(`Slot{slot}`, Base.SlotSize, centre, "shelf", true)
	end
	return parts
end

--- Pedestal centres, in slot order. Slot 1 is front-left, so the slots a new
--- player fills first are the ones nearest the door and the home pad.
function Base.slotCentres(): { Vec }
	local centres: { Vec } = {}
	for rowIndex = #Base.SlotRows, 1, -1 do
		for _, x in Base.SlotColumns do
			table.insert(centres, { x, Base.SlotSize[2] / 2, Base.SlotRows[rowIndex] })
		end
	end
	return centres
end

--- The point a squish sits at on a slot: on top of the pedestal.
function Base.slotTop(slot: number): Vec
	local centre = Base.slotCentres()[slot]
	return { centre[1], Base.SlotSize[2], centre[3] }
end

--- True when a local-frame point is inside the walls. Delivery, defence and
--- trap targeting all ask this.
function Base.insideWalls(x: number, z: number): boolean
	local inner = Base.Half - Base.WallThickness
	return math.abs(x) <= inner and z >= -inner and z <= Base.Half
end

--- True when a local-frame point is on the entrance path.
function Base.onPath(x: number, z: number): boolean
	return math.abs(x) <= Base.DoorWidth / 2 and z >= Base.Half and z <= Base.Half + Base.PathLength
end

--- Plot placement on the ring: centre and the yaw that turns +Z to the plaza.
function Base.plotTransform(index: number): (number, number, number)
	local angle = (index - 1) * (2 * math.pi / Base.PlotCount)
	local x = math.sin(angle) * Base.RingRadius
	local z = math.cos(angle) * Base.RingRadius
	-- Local +Z must point from the plot centre to the origin.
	local yaw = math.atan2(-x, -z)
	return x, z, yaw
end

--- Local to world, for the tests and the builder alike.
function Base.toWorld(index: number, lx: number, lz: number): (number, number)
	local px, pz, yaw = Base.plotTransform(index)
	local c, s = math.cos(yaw), math.sin(yaw)
	-- Rotation about Y by yaw, Roblox convention: x' = x cos + z sin, z' = -x sin + z cos.
	return px + lx * c + lz * s, pz - lx * s + lz * c
end

function Base.toLocal(index: number, wx: number, wz: number): (number, number)
	local px, pz, yaw = Base.plotTransform(index)
	local dx, dz = wx - px, wz - pz
	local c, s = math.cos(yaw), math.sin(yaw)
	return dx * c - dz * s, dx * s + dz * c
end

--- Farthest any part of a base reaches from its centre, for spacing checks.
function Base.footprintRadius(): number
	local farthest = 0
	for _, part in Base.parts() do
		for _, sx in { -1, 1 } do
			for _, sz in { -1, 1 } do
				local x = part.centre[1] + sx * part.size[1] / 2
				local z = part.centre[3] + sz * part.size[3] / 2
				farthest = math.max(farthest, math.sqrt(x * x + z * z))
			end
		end
	end
	return farthest
end

return Base
