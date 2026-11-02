--!strict
--- Everything the client does to the 3D world for this one viewer:
---
---   * the squash: when a squish is squeezed, every client watching squashes
---     it, springs it back, and floats the coins it paid;
---   * prompt labels in this player's language, and no grab prompt on the
---     player's own squishes;
---   * base signs, written in this player's language;
---   * knockback from a pillow or a trampoline, applied to the local
---     character, which is the only place a character's velocity can be set;
---   * the pillow's name in the backpack.
---
--- All of it is local and visual. Nothing here changes what the server knows.

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local TweenService = game:GetService("TweenService")

local Remotes = require(ReplicatedStorage.Shared.Remotes)
local Sounds = require(ReplicatedStorage.Shared.Config.Sounds)
local L = require(script.Parent.Parent.Locale)

local WorldController = {}

local player = Players.LocalPlayer

local squeezedSignal = Instance.new("BindableEvent")
--- Fires (model) when one of this player's own squishes is squeezed.
WorldController.OwnSqueezed = squeezedSignal.Event

local squashing: { [Model]: boolean } = {}

local function playSound(id: number, parent: Instance)
	if id == 0 then
		return
	end
	local sound = Instance.new("Sound")
	sound.SoundId = `rbxassetid://{id}`
	sound.Volume = 0.6
	sound.Parent = parent
	sound:Play()
	sound.Ended:Connect(function()
		sound:Destroy()
	end)
end

--- Squashes a model down and out, then lets it spring back with a wobble.
--- Works on any squish, primitive or mesh, by scaling every part's size and
--- its offset from the base of the model.
local function squash(model: Model)
	if squashing[model] then
		return
	end
	local body = model.PrimaryPart
	if body == nil then
		return
	end
	squashing[model] = true
	local base = body.CFrame * CFrame.new(0, -body.Size.Y / 2, 0)
	local parts: { { part: BasePart, size: Vector3, offset: CFrame } } = {}
	for _, child in model:GetDescendants() do
		if child:IsA("BasePart") then
			table.insert(parts, { part = child, size = child.Size, offset = base:ToObjectSpace(child.CFrame) })
		end
	end
	local function apply(sy: number)
		local sxz = 1 + (1 - sy) * 0.6
		local scale = Vector3.new(sxz, sy, sxz)
		for _, item in parts do
			if item.part.Parent ~= nil then
				item.part.Size = item.size * scale
				local p = item.offset.Position * scale
				item.part.CFrame = base * CFrame.new(p) * item.offset.Rotation
			end
		end
	end
	local value = Instance.new("NumberValue")
	value.Value = 1
	value.Changed:Connect(apply)
	local down = TweenService:Create(value, TweenInfo.new(0.09, Enum.EasingStyle.Quad, Enum.EasingDirection.Out), { Value = 0.62 })
	local up = TweenService:Create(value, TweenInfo.new(0.55, Enum.EasingStyle.Elastic, Enum.EasingDirection.Out), { Value = 1 })
	down:Play()
	down.Completed:Wait()
	up:Play()
	up.Completed:Wait()
	apply(1)
	value:Destroy()
	squashing[model] = nil
end

local function floatNumber(model: Model, amount: number)
	local body = model.PrimaryPart
	if body == nil then
		return
	end
	local gui = Instance.new("BillboardGui")
	gui.Size = UDim2.new(0, 120, 0, 40)
	gui.StudsOffset = Vector3.new(0, body.Size.Y + 1, 0)
	gui.AlwaysOnTop = true
	gui.Adornee = body
	local label = Instance.new("TextLabel")
	label.BackgroundTransparency = 1
	label.Size = UDim2.fromScale(1, 1)
	label.Font = Enum.Font.FredokaOne
	label.TextScaled = true
	label.TextColor3 = Color3.fromRGB(255, 200, 90)
	label.TextStrokeTransparency = 0.3
	label.Text = `+{amount}`
	label.Parent = gui
	gui.Parent = body
	TweenService:Create(gui, TweenInfo.new(0.9), { StudsOffset = gui.StudsOffset + Vector3.new(0, 3, 0) }):Play()
	TweenService:Create(label, TweenInfo.new(0.9), { TextTransparency = 1, TextStrokeTransparency = 1 }):Play()
	task.delay(1, function()
		gui:Destroy()
	end)
end

local function watchSquish(model: Instance)
	if not model:IsA("Model") then
		return
	end
	model:GetAttributeChangedSignal("SqueezedAt"):Connect(function()
		task.spawn(squash, model)
		local body = model.PrimaryPart
		if body ~= nil then
			playSound(Sounds.squeak, body)
		end
		if model:GetAttribute("OwnerUserId") == player.UserId then
			local reward = model:GetAttribute("SqueezeReward")
			if typeof(reward) == "number" then
				floatNumber(model, reward)
			end
			squeezedSignal:Fire(model)
		end
	end)
end

local function labelPrompt(prompt: Instance)
	if not prompt:IsA("ProximityPrompt") then
		return
	end
	local key = prompt:GetAttribute("TextKey")
	if typeof(key) == "string" then
		prompt.ActionText = L.text(key)
	end
	local objectKey = prompt:GetAttribute("SquishKey")
	if typeof(objectKey) == "string" then
		prompt.ObjectText = L.text(objectKey)
	end
	-- Nobody steals from themselves. The server would refuse anyway; hiding
	-- the prompt just keeps it from being offered.
	if prompt:GetAttribute("OwnerUserId") == player.UserId then
		prompt.Enabled = false
	end
end

local function labelSign(plot: Instance)
	local arch = plot:FindFirstChild("SignArch")
	local sign = if arch ~= nil then arch:FindFirstChild("Sign") else nil
	local label = if sign ~= nil then sign:FindFirstChild("Owner") else nil
	if label == nil or not label:IsA("TextLabel") then
		return
	end
	local name = plot:GetAttribute("OwnerName")
	label.Text = if typeof(name) == "string" then L.text("base.sign", name) else ""
end

local function localisePillow(tool: Instance)
	if tool:IsA("Tool") and tool.Name == "Pillow" then
		tool.Name = L.text("pillow.name")
	end
end

function WorldController.init()
	local plots = workspace:WaitForChild("Plots")
	local function watchPlot(plot: Instance)
		labelSign(plot)
		plot:GetAttributeChangedSignal("OwnerName"):Connect(function()
			labelSign(plot)
		end)
		local folder = plot:WaitForChild("Squishes", 10)
		if folder ~= nil then
			for _, model in folder:GetChildren() do
				watchSquish(model)
			end
			folder.ChildAdded:Connect(watchSquish)
		end
	end
	for _, plot in plots:GetChildren() do
		task.spawn(watchPlot, plot)
	end
	plots.ChildAdded:Connect(watchPlot)

	for _, descendant in workspace:GetDescendants() do
		labelPrompt(descendant)
	end
	workspace.DescendantAdded:Connect(function(descendant)
		if descendant:IsA("ProximityPrompt") then
			-- Attributes are set before the prompt is parented on the server,
			-- but replication can deliver them a frame apart.
			task.defer(labelPrompt, descendant)
		end
	end)
	L.Changed:Connect(function()
		for _, descendant in workspace:GetDescendants() do
			labelPrompt(descendant)
		end
		for _, plot in plots:GetChildren() do
			labelSign(plot)
		end
	end)

	Remotes.event(Remotes.Names.Knockback).OnClientEvent:Connect(function(velocity: Vector3)
		local character = player.Character
		local root = if character ~= nil then character:FindFirstChild("HumanoidRootPart") :: BasePart? else nil
		if root ~= nil then
			root.AssemblyLinearVelocity = velocity
			playSound(Sounds.boing, root)
		end
	end)

	local backpack = player:WaitForChild("Backpack")
	for _, tool in backpack:GetChildren() do
		localisePillow(tool)
	end
	backpack.ChildAdded:Connect(localisePillow)
	player.CharacterAdded:Connect(function()
		local fresh = player:WaitForChild("Backpack")
		fresh.ChildAdded:Connect(localisePillow)
	end)
end

return WorldController
