--!strict
--- Places the map's parts from the numbers in Config/Base.
---
--- Nothing here decides a size or a position: those come from Base, where the
--- tests check them. This file only turns boxes into Parts, so what the tests
--- measured is what gets built.

local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Base = require(ReplicatedStorage.Shared.Config.Base)
local Palette = require(ReplicatedStorage.Shared.Config.Palette)

local Builder = {}

local function part(name: string, size: Vector3, cframe: CFrame, colour: Color3, parent: Instance): Part
	local p = Instance.new("Part")
	p.Name = name
	p.Size = size
	p.CFrame = cframe
	p.Color = colour
	p.Anchored = true
	p.Material = Enum.Material.SmoothPlastic
	p.TopSurface = Enum.SurfaceType.Smooth
	p.BottomSurface = Enum.SurfaceType.Smooth
	p.Parent = parent
	return p
end

--- The CFrame of a plot's local origin: floor centre, +Z toward the plaza.
function Builder.plotCFrame(index: number): CFrame
	local x, z, yaw = Base.plotTransform(index)
	return CFrame.new(x, 0, z) * CFrame.Angles(0, yaw, 0)
end

function Builder.localToWorld(index: number, x: number, y: number, z: number): CFrame
	return Builder.plotCFrame(index) * CFrame.new(x, y, z)
end

function Builder.buildPlot(index: number, parent: Instance): Model
	local model = Instance.new("Model")
	model.Name = `Plot{index}`
	model:SetAttribute("PlotIndex", index)
	local origin = Builder.plotCFrame(index)
	local wallColour = Palette.colour(Palette.PlotWalls[(index - 1) % #Palette.PlotWalls + 1])

	for _, box in Base.parts() do
		local colour = if box.colour == "wall" then wallColour else Palette.colour((Palette.World :: any)[box.colour])
		local p = part(
			box.name,
			Vector3.new(box.size[1], box.size[2], box.size[3]),
			origin * CFrame.new(box.centre[1], box.centre[2], box.centre[3]),
			colour,
			model
		)
		p.CanCollide = box.solid
		if box.name == "HomePad" or string.sub(box.name, 1, 8) == "TrapSlot" then
			p.Material = Enum.Material.Neon
			p.Transparency = 0.55
		end
	end

	-- The owner's name on the arch, drawn by the client in each viewer's own
	-- language (the sign reads "Mia's base" in English and "Base de Mia" in
	-- Spanish). The server only says whose it is.
	local arch = model:FindFirstChild("SignArch") :: BasePart
	local gui = Instance.new("SurfaceGui")
	gui.Name = "Sign"
	gui.Face = Enum.NormalId.Back
	gui.SizingMode = Enum.SurfaceGuiSizingMode.PixelsPerStud
	gui.PixelsPerStud = 40
	gui.Parent = arch
	local label = Instance.new("TextLabel")
	label.Name = "Owner"
	label.Size = UDim2.fromScale(1, 1)
	label.BackgroundTransparency = 1
	label.Font = Enum.Font.FredokaOne
	label.TextScaled = true
	label.TextColor3 = Palette.colour(Palette.Ui.ink)
	label.Text = ""
	label.Parent = gui

	local squishes = Instance.new("Folder")
	squishes.Name = "Squishes"
	squishes.Parent = model
	local traps = Instance.new("Folder")
	traps.Name = "Traps"
	traps.Parent = model

	model.Parent = parent
	return model
end

--- Ground, plaza, the box machine and the show stage.
function Builder.buildPlaza(parent: Instance): Model
	local model = Instance.new("Model")
	model.Name = "Plaza"

	local ground = part(
		"Ground",
		Vector3.new(4, Base.GroundRadius * 2, Base.GroundRadius * 2),
		CFrame.new(0, -3, 0) * CFrame.Angles(0, 0, math.rad(90)),
		Palette.colour(Palette.World.ground),
		model
	)
	ground.Shape = Enum.PartType.Cylinder
	ground.Material = Enum.Material.Grass

	local plaza = part(
		"PlazaFloor",
		Vector3.new(0.4, Base.PlazaRadius * 2, Base.PlazaRadius * 2),
		CFrame.new(0, -0.8, 0) * CFrame.Angles(0, 0, math.rad(90)),
		Palette.colour(Palette.World.plaza),
		model
	)
	plaza.Shape = Enum.PartType.Cylinder

	-- The box machine: a round pastel tower with three boxes on a turntable.
	local machine = part(
		"Machine",
		Vector3.new(10, Base.MachineRadius * 2, Base.MachineRadius * 2),
		CFrame.new(0, 4, 0) * CFrame.Angles(0, 0, math.rad(90)),
		Palette.colour(Palette.World.machine),
		model
	)
	machine.Shape = Enum.PartType.Cylinder
	local cap = part(
		"MachineCap",
		Vector3.new(Base.MachineRadius * 1.6, 6, Base.MachineRadius * 1.6),
		CFrame.new(0, 12, 0),
		Palette.colour(Palette.World.accent),
		model
	)
	cap.Shape = Enum.PartType.Ball
	cap.CanCollide = false

	local prompt = Instance.new("ProximityPrompt")
	prompt.Name = "BoxPrompt"
	prompt:SetAttribute("TextKey", "box.machine")
	prompt.ActionText = ""
	prompt.HoldDuration = 0
	prompt.MaxActivationDistance = Base.MachineRadius + 8
	prompt.RequiresLineOfSight = false
	prompt.Parent = machine

	-- The show stage, a little way off the machine so the two prompts never
	-- overlap.
	local stage = part(
		"ShowStage",
		Vector3.new(14, 2, 8),
		CFrame.new(0, 0, -(Base.MachineRadius + 14)),
		Palette.colour(Palette.World.stage),
		model
	)
	local showPrompt = Instance.new("ProximityPrompt")
	showPrompt.Name = "ShowPrompt"
	showPrompt:SetAttribute("TextKey", "show.title")
	showPrompt.ActionText = ""
	showPrompt.HoldDuration = 0
	showPrompt.MaxActivationDistance = 12
	showPrompt.Parent = stage

	local spawn = Instance.new("SpawnLocation")
	spawn.Name = "PlazaSpawn"
	spawn.Size = Vector3.new(8, 1, 8)
	spawn.CFrame = CFrame.new(0, -0.4, Base.MachineRadius + 12)
	spawn.Anchored = true
	spawn.Neutral = true
	spawn.Transparency = 1
	spawn.CanCollide = false
	spawn.Parent = model

	model.Parent = parent
	return model
end

return Builder
