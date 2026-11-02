--!strict
--- Squish traps in the entrance path of each base.
---
--- Traps react only to someone carrying one of the owner's squishes, and they
--- do not act on their own: theft asks, on every step of a carry, what the
--- traps of the base being robbed do to this carrier right now. This file
--- answers and draws; theft applies. That keeps traps free of any import of
--- the theft code.

local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Base = require(ReplicatedStorage.Shared.Config.Base)
local Palette = require(ReplicatedStorage.Shared.Config.Palette)
local Remotes = require(ReplicatedStorage.Shared.Remotes)
local Traps = require(ReplicatedStorage.Shared.Config.Traps)
local Types = require(ReplicatedStorage.Shared.Types)
local Builder = require(script.Parent.Parent.World.Builder)
local DataService = require(script.Parent.DataService)
local PlotService = require(script.Parent.PlotService)
local SquishService = require(script.Parent.SquishService)

local TrapService = {}

export type Effect = {
	bounce: boolean,
	slowFactor: number?,
	slowSeconds: number?,
	knockLoose: boolean,
}

--- Per carry: which traps have already had their go. A trampoline throws once
--- per carry, so a thief bounced back in is not juggled forever.
local fired: { [Player]: { [string]: boolean } } = {}
local cannonReadyAt: { [number]: number } = {}

local random = Random.new()

function TrapService.resetCarry(carrier: Player)
	fired[carrier] = nil
end

local function onTrap(lx: number, lz: number, trap: Traps.Trap): boolean
	local z = Base.TrapSlotZ[trap.slot]
	return math.abs(lx) <= Base.TrapSize[1] / 2 and math.abs(lz - z) <= Base.TrapSize[3] / 2 + 1
end

--- Cannon reach: the whole path, and a little way past it.
local function inCannonRange(lx: number, lz: number): boolean
	return math.abs(lx) <= Base.DoorWidth and lz >= Base.Half - 2 and lz <= Base.Half + Base.PathLength + 10
end

--- What the traps of plot `plotIndex` do to a carrier at `position` now.
function TrapService.step(carrier: Player, plotIndex: number, position: Vector3): Effect
	local effect: Effect = { bounce = false, knockLoose = false }
	local owner = PlotService.owner(plotIndex)
	local data = if owner ~= nil then DataService.getData(owner) else nil
	if data == nil then
		return effect
	end
	local lx, lz = PlotService.toLocal(plotIndex, position)
	local seen = fired[carrier]
	if seen == nil then
		seen = {}
		fired[carrier] = seen
	end

	for _, trap in Traps.List do
		local level = Traps.level(trap, data.traps[trap.id] or 0)
		if level == nil then
			continue
		end
		if trap.id == "trampoline" and not seen.trampoline and onTrap(lx, lz, trap) then
			seen.trampoline = true
			if random:NextNumber() < (level.chance :: number) then
				effect.bounce = true
			end
		elseif trap.id == "slime" and onTrap(lx, lz, trap) then
			effect.slowFactor = level.slowFactor
			effect.slowSeconds = level.slowSeconds
		elseif trap.id == "cannon" and inCannonRange(lx, lz) then
			local now = os.clock()
			if now >= (cannonReadyAt[plotIndex] or 0) then
				cannonReadyAt[plotIndex] = now + (level.cooldown :: number)
				TrapService.fireCannon(plotIndex, position)
				if random:NextNumber() < (level.chance :: number) then
					effect.knockLoose = true
				end
			end
		end
	end
	return effect
end

--- The throw direction for a trampoline: up, and back toward the base.
function TrapService.bounceVelocity(plotIndex: number): Vector3
	-- The plot frame's LookVector is its local -Z, which points from the door
	-- into the base: exactly "back in".
	local inward = Builder.plotCFrame(plotIndex).LookVector
	return inward * Traps.TrampolineBack + Vector3.new(0, Traps.TrampolineUp, 0)
end

--- A pillow lobbed from the cannon at the carrier: visual only, the hit is
--- decided by the roll above.
function TrapService.fireCannon(plotIndex: number, target: Vector3)
	local model = PlotService.model(plotIndex)
	local cannon = (model:FindFirstChild("Traps") :: Folder):FindFirstChild("cannon")
	if cannon == nil or not cannon:IsA("BasePart") then
		return
	end
	local pillow = Instance.new("Part")
	pillow.Name = "CannonPillow"
	pillow.Size = Vector3.new(1.6, 0.8, 1.2)
	pillow.Color = Color3.fromRGB(255, 230, 240)
	pillow.Material = Enum.Material.SmoothPlastic
	pillow.CanCollide = false
	pillow.CanQuery = false
	pillow.Anchored = true
	local from = cannon.Position + Vector3.new(0, 2, 0)
	pillow.CFrame = CFrame.new(from)
	pillow.Parent = workspace
	task.spawn(function()
		local steps = 10
		for step = 1, steps do
			local alpha = step / steps
			local arc = math.sin(alpha * math.pi) * 4
			pillow.CFrame = CFrame.new(from:Lerp(target, alpha) + Vector3.new(0, arc, 0))
			task.wait(0.03)
		end
		pillow:Destroy()
	end)
end

--- Draws the owner's traps on their path.
function TrapService.render(player: Player)
	local data = DataService.getData(player)
	local index = PlotService.plotIndex(player)
	if data == nil or index == nil then
		return
	end
	local folder = PlotService.model(index):FindFirstChild("Traps") :: Folder
	folder:ClearAllChildren()
	for _, trap in Traps.List do
		local level = data.traps[trap.id] or 0
		if level < 1 then
			continue
		end
		local z = Base.TrapSlotZ[trap.slot]
		local colour = Palette.colour(trap.colour)
		local p = Instance.new("Part")
		p.Name = trap.id
		p.Anchored = true
		p.CanCollide = false
		p.Color = colour
		p.Material = Enum.Material.SmoothPlastic
		if trap.id == "trampoline" then
			p.Shape = Enum.PartType.Cylinder
			p.Size = Vector3.new(0.6, 6 + level, 6 + level)
			p.CFrame = Builder.localToWorld(index, 0, 0.3, z) * CFrame.Angles(0, 0, math.rad(90))
		elseif trap.id == "slime" then
			p.Shape = Enum.PartType.Cylinder
			p.Size = Vector3.new(0.2, Base.TrapSize[1] - 1, Base.TrapSize[1] - 1)
			p.CFrame = Builder.localToWorld(index, 0, 0.1, z) * CFrame.Angles(0, 0, math.rad(90))
			p.Material = Enum.Material.Glass
			p.Transparency = 0.25
		else
			p.Size = Vector3.new(2 + level * 0.3, 2 + level * 0.3, 3)
			p.CFrame = Builder.localToWorld(index, Base.DoorWidth / 2 + 2, 1.2, z)
		end
		p:SetAttribute("Level", level)
		p.Parent = folder
	end
end

local function upgrade(player: Player, data: Types.ProfileData, request: { [string]: any })
	local trap = Traps.get(request.trap)
	if trap == nil then
		return
	end
	local level = data.traps[trap.id] or 0
	local cost = Traps.nextCost(trap, level)
	if cost == nil then
		return
	end
	if not SquishService.spendCoins(player, data, cost, `trap:{trap.id}`) then
		Remotes.toast(player, "box.notEnough")
		return
	end
	data.traps[trap.id] = level + 1
	TrapService.render(player)
end

function TrapService.start()
	SquishService.registerAction("upgradeTrap", function(player, data, request)
		if typeof(request.trap) == "string" then
			upgrade(player, data, request)
		end
	end)
	PlotService.Claimed:Connect(function(player: Player)
		TrapService.render(player)
	end)
	PlotService.Released:Connect(function(player: Player, index: number)
		fired[player] = nil
		cannonReadyAt[index] = nil
	end)
end

return TrapService
