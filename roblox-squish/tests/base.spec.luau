--!strict
--- The map, checked by arithmetic.
---
--- Nobody has stood in this base: there is no Studio here. These tests are the
--- substitute -- each one is a thing a first playtest would otherwise find by
--- walking into it.
local Base = require("../src/shared/Config/Base")
local Economy = require("../src/shared/Config/Economy")
local Steal = require("../src/shared/Config/Steal")
local Traps = require("../src/shared/Config/Traps")
local t = require("./harness")

local EPS = 1e-6

type Box = Base.Box

local function overlap(a: Box, b: Box): number
	local volume = 1
	for axis = 1, 3 do
		local lo = math.max(a.centre[axis] - a.size[axis] / 2, b.centre[axis] - b.size[axis] / 2)
		local hi = math.min(a.centre[axis] + a.size[axis] / 2, b.centre[axis] + b.size[axis] / 2)
		if hi - lo <= EPS then
			return 0
		end
		volume *= hi - lo
	end
	return volume
end

local function contains(box: Box, x: number, y: number, z: number): boolean
	return math.abs(x - box.centre[1]) <= box.size[1] / 2 + EPS
		and math.abs(y - box.centre[2]) <= box.size[2] / 2 + EPS
		and math.abs(z - box.centre[3]) <= box.size[3] / 2 + EPS
end

local function byPrefix(prefix: string): { Box }
	local found: { Box } = {}
	for _, part in Base.parts() do
		if string.sub(part.name, 1, #prefix) == prefix then
			table.insert(found, part)
		end
	end
	return found
end

--- Shortest walk from a to b around a circular obstacle at the origin.
local function walkAround(ax: number, az: number, bx: number, bz: number, radius: number): number
	local dx, dz = bx - ax, bz - az
	local length = math.sqrt(dx * dx + dz * dz)
	local along = -(ax * dx + az * dz) / (length * length)
	along = math.clamp(along, 0, 1)
	local cx, cz = ax + dx * along, az + dz * along
	if math.sqrt(cx * cx + cz * cz) >= radius then
		return length
	end
	local da = math.sqrt(ax * ax + az * az)
	local db = math.sqrt(bx * bx + bz * bz)
	local ta = math.sqrt(da * da - radius * radius)
	local tb = math.sqrt(db * db - radius * radius)
	local between = math.acos(math.clamp((ax * bx + az * bz) / (da * db), -1, 1))
	local arc = between - math.acos(radius / da) - math.acos(radius / db)
	return ta + tb + radius * math.max(0, arc)
end

return function()
	t.suite("Base: walls and joints")

	t.test("no two solid parts overlap", function()
		local parts = Base.parts()
		for i = 1, #parts do
			for j = i + 1, #parts do
				local a, b = parts[i], parts[j]
				if a.solid and b.solid then
					local shared = overlap(a, b)
					if shared > 0 then
						error(`{a.name} and {b.name} overlap by {shared} cubic studs`, 0)
					end
				end
			end
		end
	end)

	t.test("the wall ring is closed everywhere except the door", function()
		-- Walk the centre line of the wall band all the way round, every quarter
		-- stud, at mid height. Every point is inside a wall or inside the door.
		local walls = byPrefix("Wall")
		local line = Base.Half - Base.WallThickness / 2
		local y = Base.WallHeight / 2
		local step = 0.25
		local gaps: { string } = {}
		local position = -line
		while position <= line + EPS do
			local points = {
				{ position, -line, "back" },
				{ position, line, "front" },
				{ -line, position, "left" },
				{ line, position, "right" },
			}
			for _, point in points do
				local x, z, side = point[1] :: number, point[2] :: number, point[3] :: string
				local inDoor = side == "front" and math.abs(x) < Base.DoorWidth / 2 - EPS
				local covered = false
				for _, wall in walls do
					if contains(wall, x, y, z) then
						covered = true
						break
					end
				end
				if covered == inDoor then
					table.insert(gaps, `{side} wall at {x},{z}: {if inDoor then "door blocked" else "gap"}`)
				end
			end
			position += step
		end
		if #gaps > 0 then
			error(`{#gaps} problem(s), first: {gaps[1]}`, 0)
		end
	end)

	t.test("the door fits a carrier with room to dodge a defender", function()
		t.greaterThan(Base.DoorWidth, 4 * Base.CharacterWidth, "door width")
	end)

	t.test("the walls cannot be jumped, even from a pedestal", function()
		local highestFloor = 0
		for _, part in Base.parts() do
			if part.solid and string.sub(part.name, 1, 4) ~= "Wall" and part.name ~= "SignArch" then
				highestFloor = math.max(highestFloor, part.centre[2] + part.size[2] / 2)
			end
		end
		t.greaterThan(Base.WallHeight, highestFloor + Base.JumpHeight + 1, "wall height over reachable feet")
	end)

	t.suite("Base: shelves, pad and traps")

	t.test("there is a pedestal for every shelf the economy can sell", function()
		local total = Economy.StartSlots + Economy.MaxBoughtSlots + Economy.PassSlots
		t.equal(#Base.slotCentres(), Base.SlotCount, "slot centres")
		t.equal(Base.SlotCount, total, "pedestals vs purchasable shelves")
	end)

	t.test("pedestals leave a walkway between each other and the walls", function()
		local inner = Base.Half - Base.WallThickness
		local centres = Base.slotCentres()
		for i, a in centres do
			local edgeGap = inner - (math.abs(a[1]) + Base.SlotSize[1] / 2)
			t.greaterThan(edgeGap, Base.CharacterWidth, `slot {i} to side wall`)
			local backGap = (a[3] - Base.SlotSize[3] / 2) - (-inner)
			t.greaterThan(backGap, Base.CharacterWidth, `slot {i} to back wall`)
			for j = i + 1, #centres do
				local b = centres[j]
				local gapX = math.abs(a[1] - b[1]) - Base.SlotSize[1]
				local gapZ = math.abs(a[3] - b[3]) - Base.SlotSize[3]
				t.greaterThan(math.max(gapX, gapZ), Base.CharacterWidth, `slots {i} and {j}`)
			end
		end
	end)

	t.test("the first slots filled are the ones nearest the door", function()
		local centres = Base.slotCentres()
		t.greaterThan(centres[1][3], centres[#centres][3], "slot 1 is in the front row")
	end)

	t.test("the home pad is inside the walls and clear of every pedestal", function()
		local pad = Base.HomePad
		local half = { pad.size[1] / 2, pad.size[3] / 2 }
		for _, sx in { -1, 1 } do
			for _, sz in { -1, 1 } do
				t.isTrue(
					Base.insideWalls(pad.centre[1] + sx * half[1], pad.centre[3] + sz * half[2]),
					"pad corner inside walls"
				)
			end
		end
		for slot, centre in Base.slotCentres() do
			local gapZ = (pad.centre[3] - half[2]) - (centre[3] + Base.SlotSize[3] / 2)
			local gapX = math.abs(pad.centre[1] - centre[1]) - half[1] - Base.SlotSize[1] / 2
			t.greaterThan(math.max(gapX, gapZ), Base.CharacterWidth, `pad to slot {slot}`)
		end
	end)

	t.test("each trap has a slot on the path and they do not touch", function()
		t.equal(#Base.TrapSlotZ, #Traps.List, "trap slots")
		for _, trap in Traps.List do
			local z = Base.TrapSlotZ[trap.slot]
			assert(z ~= nil, `{trap.id} has a slot`)
			t.isTrue(Base.onPath(0, z - Base.TrapSize[3] / 2), `{trap.id} starts on the path`)
			t.isTrue(Base.onPath(0, z + Base.TrapSize[3] / 2), `{trap.id} ends on the path`)
			t.isTrue(Base.TrapSize[1] <= Base.DoorWidth, `{trap.id} fits the path width`)
		end
		for i = 2, #Base.TrapSlotZ do
			t.greaterThan(Base.TrapSlotZ[i] - Base.TrapSlotZ[i - 1], Base.TrapSize[3], `trap slots {i - 1} and {i}`)
		end
	end)

	t.suite("Base: the ring")

	t.test("local and world frames round-trip, and the door faces the plaza", function()
		for index = 1, Base.PlotCount do
			local wx, wz = Base.toWorld(index, 3, 7)
			local lx, lz = Base.toLocal(index, wx, wz)
			t.near(lx, 3, `plot {index} x`, 1e-9)
			t.near(lz, 7, `plot {index} z`, 1e-9)
			local px, pz = Base.toWorld(index, 0, 0)
			local dx, dz = Base.toWorld(index, 0, Base.Half)
			t.lessThan(math.sqrt(dx * dx + dz * dz), math.sqrt(px * px + pz * pz), `plot {index} door is nearer the plaza`)
		end
	end)

	t.test("neighbouring bases do not touch, and none reaches the plaza", function()
		local reach = Base.footprintRadius()
		local x1, z1 = Base.plotTransform(1)
		local x2, z2 = Base.plotTransform(2)
		local spacing = math.sqrt((x1 - x2) ^ 2 + (z1 - z2) ^ 2)
		t.greaterThan(spacing, 2 * reach + 4, "centre spacing against two footprints")
		t.greaterThan(Base.RingRadius - reach, Base.PlazaRadius, "bases stay out of the plaza")
		t.greaterThan(Base.GroundRadius, Base.RingRadius + reach + 10, "bases stay on the ground")
		t.greaterThan(Base.PlazaRadius, Base.MachineRadius + 10, "room to walk round the machine")
	end)

	t.test("the longest possible carry fits inside the carry timeout", function()
		-- Back corner of one base, out of its door, round the machine, into the
		-- opposite base's door and onto its pad, at the slowest carry speed, with
		-- the worst slime in the way.
		local worst = 0
		local farSlot = Base.slotCentres()[Base.SlotCount]
		for from = 1, Base.PlotCount do
			for to = 1, Base.PlotCount do
				if from ~= to then
					local sx, sz = Base.toWorld(from, farSlot[1], farSlot[3])
					local ax, az = Base.toWorld(from, 0, Base.Half)
					local bx, bz = Base.toWorld(to, 0, Base.Half)
					local hx, hz = Base.toWorld(to, Base.HomePad.centre[1], Base.HomePad.centre[3])
					local inside = math.sqrt((sx - ax) ^ 2 + (sz - az) ^ 2)
					local across = walkAround(ax, az, bx, bz, Base.MachineRadius + Base.CharacterWidth)
					local home = math.sqrt((bx - hx) ^ 2 + (bz - hz) ^ 2)
					worst = math.max(worst, inside + across + home)
				end
			end
		end
		local slowest = Steal.carrySpeed(Economy.MaxTier)
		local slime = Traps.get("slime")
		assert(slime ~= nil)
		local worstSlime = slime.levels[#slime.levels]
		local slowFactor = worstSlime.slowFactor :: number
		local slowSeconds = worstSlime.slowSeconds :: number
		local slimeLoss = slowSeconds * (1 - slowFactor)
		local seconds = worst / slowest + slimeLoss
		t.lessThan(seconds * 1.15, Steal.CarryTimeoutSeconds, `worst carry of {math.floor(worst)} studs`)
	end)
end
