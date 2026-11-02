--!strict
--- The always-on interface: coins, income, timers, the menu buttons, toasts.
---
--- Built to be read in a glance by a child on a phone: the coin count is the
--- biggest thing on screen, the buttons are big and few, and every message
--- arrives as a short toast that fades by itself.

local ReplicatedStorage = game:GetService("ReplicatedStorage")
local TweenService = game:GetService("TweenService")

local Remotes = require(ReplicatedStorage.Shared.Remotes)
local L = require(script.Parent.Parent.Locale)
local State = require(script.Parent.Parent.State)
local Ui = require(script.Parent.Parent.Ui)

local HudController = {}

local gui: ScreenGui
local coinsLabel: TextLabel
local incomeLabel: TextLabel
local timersLabel: TextLabel
local toastHolder: Frame
local buttonBar: Frame
local carryBanner: TextLabel

local buttons: { [string]: TextButton } = {}

--- Adds a menu button. Panels register themselves, so the HUD does not need
--- to know what panels exist.
function HudController.addButton(key: string, order: number, onPress: () -> ()): TextButton
	local button = Ui.button(buttonBar, L.text(key), "button")
	button.Name = key
	button.LayoutOrder = order
	button.Size = UDim2.new(0, 120, 0, 52)
	button.TextSize = 20
	button.Activated:Connect(onPress)
	buttons[key] = button
	return button
end

function HudController.button(key: string): TextButton?
	return buttons[key]
end

--- Shows a short message. Arguments starting with "@" are string keys and are
--- translated here, in this player's language.
function HudController.toast(key: string, ...: any)
	local args = table.pack(...)
	for index = 1, args.n do
		local value = args[index]
		if typeof(value) == "string" and string.sub(value, 1, 1) == "@" then
			args[index] = L.text(string.sub(value, 2))
		end
	end
	local text = L.text(key, table.unpack(args, 1, args.n))
	local label = Ui.label(toastHolder, text, 20, "ink")
	label.BackgroundTransparency = 0.05
	label.BackgroundColor3 = Ui.colour("panel")
	label.Size = UDim2.new(1, 0, 0, 42)
	label.AutomaticSize = Enum.AutomaticSize.Y
	Ui.corner(label, 12)
	Ui.padding(label, 8)
	task.delay(3.5, function()
		local fade = TweenService:Create(label, TweenInfo.new(0.4), { TextTransparency = 1, BackgroundTransparency = 1 })
		fade:Play()
		fade.Completed:Wait()
		label:Destroy()
	end)
end

local function refreshTimers()
	local state = State.current
	if state == nil then
		timersLabel.Text = ""
		return
	end
	local now = State.serverNow()
	local lines: { string } = {}
	if (state.protectedFor or 0) > 0 then
		local left = state.protectedFor - (os.clock() - State.receivedAt)
		if left > 0 then
			table.insert(lines, L.text("base.protected", Ui.clock(left)))
		end
	end
	if state.shieldUntil > now then
		table.insert(lines, L.text("base.shield", Ui.clock(state.shieldUntil - now)))
	end
	local boosts = state.boosts or {}
	local boostUntil = math.max(boosts.ad or 0, boosts.paid or 0)
	if boostUntil > now and state.multiplier > 1 then
		table.insert(lines, L.text("hud.boost", state.multiplier, Ui.clock(boostUntil - now)))
	end
	timersLabel.Text = table.concat(lines, "\n")
end

function HudController.init()
	gui = Ui.screen("Hud", 1)

	local top = Instance.new("Frame")
	top.Name = "Top"
	top.AnchorPoint = Vector2.new(0.5, 0)
	top.Position = UDim2.new(0.5, 0, 0, 8)
	top.Size = UDim2.new(0, 300, 0, 74)
	top.BackgroundColor3 = Ui.colour("panel")
	top.Parent = gui
	Ui.corner(top, 20)
	Ui.stroke(top, Ui.colour("coin"), 3)

	coinsLabel = Ui.label(top, "0", 34, "ink")
	coinsLabel.Position = UDim2.new(0, 0, 0, 2)
	coinsLabel.Size = UDim2.new(1, 0, 0, 40)
	incomeLabel = Ui.label(top, "", 18, "muted")
	incomeLabel.Position = UDim2.new(0, 0, 0, 42)
	incomeLabel.Size = UDim2.new(1, 0, 0, 26)

	timersLabel = Ui.label(gui, "", 16, "ink")
	timersLabel.AnchorPoint = Vector2.new(0.5, 0)
	timersLabel.Position = UDim2.new(0.5, 0, 0, 88)
	timersLabel.Size = UDim2.new(0, 360, 0, 60)
	timersLabel.TextStrokeTransparency = 0.6
	timersLabel.TextStrokeColor3 = Ui.colour("panel")

	buttonBar = Instance.new("Frame")
	buttonBar.Name = "Buttons"
	buttonBar.BackgroundTransparency = 1
	buttonBar.AnchorPoint = Vector2.new(0, 0.5)
	buttonBar.Position = UDim2.new(0, 10, 0.5, 0)
	buttonBar.Size = UDim2.new(0, 130, 0, 260)
	buttonBar.Parent = gui
	Ui.list(buttonBar, 10)

	toastHolder = Instance.new("Frame")
	toastHolder.Name = "Toasts"
	toastHolder.BackgroundTransparency = 1
	toastHolder.AnchorPoint = Vector2.new(0.5, 1)
	toastHolder.Position = UDim2.new(0.5, 0, 1, -90)
	toastHolder.Size = UDim2.new(0, 420, 0, 200)
	toastHolder.Parent = gui
	local layout = Ui.list(toastHolder, 6)
	layout.VerticalAlignment = Enum.VerticalAlignment.Bottom

	carryBanner = Ui.label(gui, "", 30, "buttonInk")
	carryBanner.AnchorPoint = Vector2.new(0.5, 0)
	carryBanner.Position = UDim2.new(0.5, 0, 0, 150)
	carryBanner.Size = UDim2.new(0, 320, 0, 50)
	carryBanner.BackgroundColor3 = Ui.colour("button")
	carryBanner.BackgroundTransparency = 0
	carryBanner.Visible = false
	Ui.corner(carryBanner, 16)

	State.CoinsChanged:Connect(function(coins: number)
		coinsLabel.Text = Ui.short(coins)
	end)
	State.Changed:Connect(function(state)
		incomeLabel.Text = L.text("common.perSecond", Ui.short(state.income))
		refreshTimers()
	end)
	Remotes.event(Remotes.Names.Toast).OnClientEvent:Connect(HudController.toast)
	Remotes.event(Remotes.Names.CarryState).OnClientEvent:Connect(function(carrying: boolean)
		carryBanner.Text = L.text("steal.carrying")
		carryBanner.Visible = carrying
	end)

	task.spawn(function()
		while true do
			task.wait(1)
			refreshTimers()
		end
	end)
end

return HudController
