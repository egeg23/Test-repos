--!strict
--- The box machine: choosing a box, seeing its odds, and the unboxing.
---
--- Odds are printed from Config/Boxes -- the same weights the server rolls
--- with -- on every box card, before any button. For the Robux box that is
--- Roblox policy on paid random items; for the coin boxes it is just fair.
--- The Robux box only appears when the server says this player may be shown
--- paid random items at all.

local ProximityPromptService = game:GetService("ProximityPromptService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local SoundService = game:GetService("SoundService")
local TweenService = game:GetService("TweenService")

local Boxes = require(ReplicatedStorage.Shared.Config.Boxes)
local Monetization = require(ReplicatedStorage.Shared.Config.Monetization)
local Remotes = require(ReplicatedStorage.Shared.Remotes)
local SquishModel = require(ReplicatedStorage.Shared.Render.SquishModel)
local Squishes = require(ReplicatedStorage.Shared.Config.Squishes)
local Sounds = require(ReplicatedStorage.Shared.Config.Sounds)
local L = require(script.Parent.Parent.Locale)
local State = require(script.Parent.Parent.State)
local Ui = require(script.Parent.Parent.Ui)

local BoxController = {}

local gui: ScreenGui
local panel: Frame
local body: ScrollingFrame
local reveal: Frame

local opened = Instance.new("BindableEvent")
--- Fires (speciesId, rarity) after the reveal finishes. Onboarding listens.
BoxController.Opened = opened.Event
local shown = Instance.new("BindableEvent")
BoxController.Shown = shown.Event

local firstOpenButton: TextButton? = nil

function BoxController.firstOpenButton(): TextButton?
	return firstOpenButton
end

local function play(soundId: number)
	if soundId == 0 then
		return
	end
	local sound = Instance.new("Sound")
	sound.SoundId = `rbxassetid://{soundId}`
	sound.Parent = SoundService
	sound:Play()
	sound.Ended:Connect(function()
		sound:Destroy()
	end)
end

local function oddsBlock(parent: Instance, box: Boxes.Box)
	local frame = Instance.new("Frame")
	frame.BackgroundTransparency = 1
	frame.Size = UDim2.new(1, 0, 0, 0)
	frame.AutomaticSize = Enum.AutomaticSize.Y
	frame.Parent = parent
	Ui.list(frame, 2)
	local heading = Ui.label(frame, L.text("box.odds"), 16, "muted")
	heading.TextXAlignment = Enum.TextXAlignment.Left
	for order, rarity in Squishes.RarityOrder do
		local percent = Boxes.oddsPercent(box, rarity)
		local row = Ui.label(frame, `{L.text(`rarity.{rarity}`)}  {string.format("%g", percent)}%`, 16, "ink")
		row.LayoutOrder = order
		row.Size = UDim2.new(1, 0, 0, 20)
		row.TextXAlignment = Enum.TextXAlignment.Left
		row.TextColor3 = if percent > 0 then Ui.rarityColour(rarity):Lerp(Ui.colour("ink"), 0.55) else Ui.colour("muted")
	end
	local pity = box.pity
	if pity ~= nil then
		local line = Ui.label(frame, L.text("box.pity", L.text(`rarity.{pity.rarity}`), pity.within), 15, "ink")
		line.LayoutOrder = 10
		line.TextXAlignment = Enum.TextXAlignment.Left
		line.AutomaticSize = Enum.AutomaticSize.Y
		local state = State.current
		local since = if state ~= nil and state.pity ~= nil then state.pity[box.id] or 0 else 0
		local left = Ui.label(frame, L.text("box.pityLeft", pity.within - since), 15, "muted")
		left.LayoutOrder = 11
		left.TextXAlignment = Enum.TextXAlignment.Left
	end
end

local function card(box: Boxes.Box, order: number)
	local frame = Instance.new("Frame")
	frame.LayoutOrder = order
	frame.Size = UDim2.new(1, -8, 0, 0)
	frame.AutomaticSize = Enum.AutomaticSize.Y
	frame.BackgroundColor3 = Color3.fromRGB(box.colour[1], box.colour[2], box.colour[3]):Lerp(Color3.new(1, 1, 1), 0.55)
	frame.Parent = body
	Ui.corner(frame, 16)
	Ui.padding(frame, 12)
	Ui.list(frame, 6)

	local title = Ui.label(frame, L.text(`box.{box.id}`), 24, "ink")
	title.TextXAlignment = Enum.TextXAlignment.Left
	oddsBlock(frame, box)

	local state = State.current
	local firstFree = state ~= nil and state.boxesOpened == 0 and box.id == "caramel"
	local priceText: string
	if box.paid then
		local product = nil
		for _, candidate in Monetization.Products do
			if candidate.paidBox == box.id then
				product = candidate
			end
		end
		priceText = L.text("common.robux", if product ~= nil then product.robux else 0)
		local note = Ui.label(frame, L.text("box.paidNote"), 14, "muted")
		note.AutomaticSize = Enum.AutomaticSize.Y
		note.LayoutOrder = 20
	else
		priceText = if firstFree then L.text("box.open") else L.text("common.coins", Ui.short(box.coins :: number))
	end

	local button = Ui.button(frame, `{L.text("box.open")} · {priceText}`, if box.paid then "ad" else "button")
	button.LayoutOrder = 30
	button.Size = UDim2.new(1, 0, 0, 48)
	if firstFree then
		button.Text = L.text("box.open")
		firstOpenButton = button
	end
	button.Activated:Connect(function()
		if box.paid then
			Remotes.event(Remotes.Names.PromptPurchase):FireServer("product", "rainbowBox")
		else
			Remotes.event(Remotes.Names.OpenBox):FireServer(box.id)
		end
	end)
end

local function rebuild(shop: { [string]: any }?)
	Ui.clear(body)
	firstOpenButton = nil
	local paidAllowed = shop ~= nil and shop.paidRandomAllowed == true
	for order, box in Boxes.List do
		if not box.paid or paidAllowed then
			card(box, order)
		end
	end
end

function BoxController.open()
	-- The server answers whether this player may see the paid box. Until it
	-- has, the paid box is simply not drawn.
	rebuild(nil)
	panel.Visible = true
	shown:Fire()
	task.spawn(function()
		local ok, shop = pcall(function()
			return Remotes.func(Remotes.Names.GetShop):InvokeServer()
		end)
		if ok and panel.Visible then
			rebuild(shop)
		end
	end)
end

--- The reveal: the box shakes, pops, and the squish spins in a viewport with
--- its name in its rarity colour.
local function showReveal(boxId: string, speciesId: string, rarity: string, toPocket: boolean)
	panel.Visible = false
	Ui.clear(reveal)
	reveal.Visible = true
	play(Sounds.unbox)

	local box = Boxes.get(boxId)
	local colour = if box ~= nil then Color3.fromRGB(box.colour[1], box.colour[2], box.colour[3]) else Ui.colour("button")
	local crate = Instance.new("Frame")
	crate.AnchorPoint = Vector2.new(0.5, 0.5)
	crate.Position = UDim2.fromScale(0.5, 0.45)
	crate.Size = UDim2.new(0, 150, 0, 150)
	crate.BackgroundColor3 = colour
	crate.Parent = reveal
	Ui.corner(crate, 26)
	Ui.stroke(crate, Color3.new(1, 1, 1), 6)
	for i = 1, 8 do
		crate.Rotation = if i % 2 == 0 then 8 else -8
		task.wait(0.07)
	end
	crate.Rotation = 0
	local pop = TweenService:Create(crate, TweenInfo.new(0.18), { Size = UDim2.new(0, 260, 0, 260), BackgroundTransparency = 1 })
	pop:Play()
	pop.Completed:Wait()
	crate:Destroy()
	play(Sounds.pop)

	local viewport = Instance.new("ViewportFrame")
	viewport.AnchorPoint = Vector2.new(0.5, 0.5)
	viewport.Position = UDim2.fromScale(0.5, 0.42)
	viewport.Size = UDim2.new(0, 260, 0, 260)
	viewport.BackgroundTransparency = 1
	viewport.Parent = reveal
	local model = SquishModel.build(speciesId, 1)
	model.Parent = viewport
	local camera = Instance.new("Camera")
	camera.FieldOfView = 40
	camera.Parent = viewport
	viewport.CurrentCamera = camera
	local centre = (model.PrimaryPart :: BasePart).Position
	local spin = 0
	local connection = RunService.RenderStepped:Connect(function(dt)
		spin += dt * 1.4
		camera.CFrame = CFrame.lookAt(centre + Vector3.new(math.sin(spin) * 7, 2, -math.cos(spin) * 7), centre)
	end)

	local name = Ui.label(reveal, L.text(`squish.{speciesId}`), 34, "ink")
	name.AnchorPoint = Vector2.new(0.5, 0)
	name.Position = UDim2.new(0.5, 0, 0.42, 140)
	name.Size = UDim2.new(0, 400, 0, 44)
	local rarityLabel = Ui.label(reveal, L.text(`rarity.{rarity}`), 24, "ink")
	rarityLabel.AnchorPoint = Vector2.new(0.5, 0)
	rarityLabel.Position = UDim2.new(0.5, 0, 0.42, 184)
	rarityLabel.Size = UDim2.new(0, 400, 0, 32)
	rarityLabel.TextColor3 = Ui.rarityColour(rarity)
	rarityLabel.TextStrokeTransparency = 0.4
	if toPocket then
		local pocket = Ui.label(reveal, L.text("box.toPocket"), 16, "muted")
		pocket.AnchorPoint = Vector2.new(0.5, 0)
		pocket.Position = UDim2.new(0.5, 0, 0.42, 220)
		pocket.Size = UDim2.new(0, 420, 0, 40)
	end

	local done = false
	local function finish()
		if done then
			return
		end
		done = true
		connection:Disconnect()
		reveal.Visible = false
		Ui.clear(reveal)
		opened:Fire(speciesId, rarity)
	end
	local tap = Instance.new("TextButton")
	tap.BackgroundTransparency = 1
	tap.Text = ""
	tap.Size = UDim2.fromScale(1, 1)
	tap.Parent = reveal
	tap.Activated:Connect(finish)
	task.delay(3.2, finish)
end

function BoxController.init()
	gui = Ui.screen("Boxes", 5)
	panel, body = Ui.panel(gui, L.text("box.title"), 460, 620)

	reveal = Instance.new("Frame")
	reveal.Name = "Reveal"
	reveal.Size = UDim2.fromScale(1, 1)
	reveal.BackgroundColor3 = Ui.colour("panel")
	reveal.BackgroundTransparency = 0.2
	reveal.Visible = false
	reveal.Parent = gui

	ProximityPromptService.PromptTriggered:Connect(function(prompt: ProximityPrompt)
		if prompt.Name == "BoxPrompt" then
			BoxController.open()
		end
	end)
	Remotes.event(Remotes.Names.Unboxed).OnClientEvent:Connect(function(boxId, speciesId, rarity, toPocket)
		task.spawn(showReveal, boxId, speciesId, rarity, toPocket)
	end)
	-- A bought rainbow box arrives the same way, through Unboxed, once its
	-- receipt has been processed on the server.
end

return BoxController
