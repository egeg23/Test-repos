--!strict
--- The first minute, shown and not told.
---
--- No text tutorial. A glowing arrow from the player to where they should go,
--- and a pulsing hand on what they should press:
---
---   1. the arrow points at the box machine, the hand at the free box;
---   2. after the reveal, the arrow points at the new squish on the shelf;
---   3. the first squeeze finishes it, and the server remembers.
---
--- If the player wanders off and does something else first, the guide simply
--- moves to the next step it can see is still missing.

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local TweenService = game:GetService("TweenService")

local Remotes = require(ReplicatedStorage.Shared.Remotes)
local State = require(script.Parent.Parent.State)
local BoxController = require(script.Parent.BoxController)
local WorldController = require(script.Parent.WorldController)

local OnboardingController = {}

local player = Players.LocalPlayer

local beam: Beam? = nil
local fromAttachment: Attachment? = nil
local toAttachment: Attachment? = nil
local hand: TextLabel? = nil
local finished = false

local function clearArrow()
	if beam ~= nil then
		beam:Destroy()
		beam = nil
	end
	if fromAttachment ~= nil then
		fromAttachment:Destroy()
		fromAttachment = nil
	end
	if toAttachment ~= nil then
		toAttachment:Destroy()
		toAttachment = nil
	end
end

--- A bright animated beam from the player's feet to a part.
local function arrowTo(target: BasePart?)
	clearArrow()
	local character = player.Character
	local root = if character ~= nil then character:FindFirstChild("HumanoidRootPart") :: BasePart? else nil
	if target == nil or root == nil then
		return
	end
	local a0 = Instance.new("Attachment")
	a0.Position = Vector3.new(0, -2.5, 0)
	a0.Parent = root
	local a1 = Instance.new("Attachment")
	a1.Position = Vector3.new(0, target.Size.Y / 2 + 1, 0)
	a1.Parent = target
	local b = Instance.new("Beam")
	b.Attachment0 = a0
	b.Attachment1 = a1
	b.Width0 = 1.4
	b.Width1 = 1.4
	b.FaceCamera = true
	b.LightEmission = 0.6
	b.Color = ColorSequence.new(Color3.fromRGB(255, 170, 210), Color3.fromRGB(170, 220, 255))
	b.Texture = "rbxasset://textures/particles/sparkles_main.dds"
	b.TextureMode = Enum.TextureMode.Wrap
	b.TextureLength = 3
	b.TextureSpeed = 1.5
	b.Parent = root
	beam, fromAttachment, toAttachment = b, a0, a1
end

local function clearHand()
	if hand ~= nil then
		hand:Destroy()
		hand = nil
	end
end

--- A pulsing pointing hand over a button. An emoji, not a word, so it needs
--- no translation.
local function handOn(button: GuiObject?)
	clearHand()
	if button == nil then
		return
	end
	local label = Instance.new("TextLabel")
	label.BackgroundTransparency = 1
	label.Text = "👆"
	label.TextScaled = true
	label.Size = UDim2.new(0, 48, 0, 48)
	label.AnchorPoint = Vector2.new(0.5, 0)
	label.Position = UDim2.new(0.5, 0, 1, -6)
	label.ZIndex = 20
	label.Parent = button
	TweenService:Create(
		label,
		TweenInfo.new(0.5, Enum.EasingStyle.Sine, Enum.EasingDirection.InOut, -1, true),
		{ Position = UDim2.new(0.5, 0, 1, 6) }
	):Play()
	hand = label
end

local function machine(): BasePart?
	local plaza = workspace:FindFirstChild("Plaza")
	return if plaza ~= nil then plaza:FindFirstChild("Machine") :: BasePart? else nil
end

local function ownSquish(): BasePart?
	local state = State.current
	if state == nil or state.plot == nil then
		return nil
	end
	local plots = workspace:FindFirstChild("Plots")
	local plot = if plots ~= nil then plots:FindFirstChild(`Plot{state.plot}`) else nil
	local folder = if plot ~= nil then plot:FindFirstChild("Squishes") else nil
	if folder == nil then
		return nil
	end
	for _, model in folder:GetChildren() do
		if model:IsA("Model") and model.PrimaryPart ~= nil then
			return model.PrimaryPart
		end
	end
	return nil
end

local function finish()
	if finished then
		return
	end
	finished = true
	clearArrow()
	clearHand()
	Remotes.event(Remotes.Names.OnboardingDone):FireServer()
end

local function update()
	local state = State.current
	if finished or state == nil then
		return
	end
	if state.onboardingDone then
		finished = true
		clearArrow()
		clearHand()
		return
	end
	if state.boxesOpened == 0 then
		arrowTo(machine())
	else
		clearHand()
		arrowTo(ownSquish())
	end
end

function OnboardingController.init()
	State.Changed:Connect(update)
	BoxController.Shown:Connect(function()
		if not finished then
			task.wait(0.1)
			handOn(BoxController.firstOpenButton())
		end
	end)
	BoxController.Opened:Connect(function()
		clearHand()
		task.wait(0.3)
		update()
	end)
	WorldController.OwnSqueezed:Connect(finish)
	player.CharacterAdded:Connect(function()
		task.wait(1)
		update()
	end)
end

return OnboardingController
