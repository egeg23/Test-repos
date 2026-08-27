--!strict
--- The persistent readout: points, year, progress, streak, boosts.
---
--- Before this, a player could not see their own balance without opening a
--- panel, and could not see how close they were to the next year at all. That is
--- not a missing feature so much as a missing game: every reward in the design
--- lands on a number the player had no way to watch move.
---
--- It also owns the toolbar. The three panels each grew their own toggle button
--- at a hand-picked pixel offset, which meant nothing stopped two of them
--- overlapping and nothing closed one when another opened. Registering here gives
--- one row, laid out by a list, with one panel open at a time.

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Remotes = require(ReplicatedStorage.Shared.Remotes)
local L = require(script.Parent.Parent.Locale)

local HudController = {}

local player = Players.LocalPlayer

local PANEL = Color3.fromRGB(28, 30, 38)
local ACCENT = Color3.fromRGB(70, 96, 190)
local GOLD = Color3.fromRGB(206, 166, 78)
local TEXT = Color3.fromRGB(236, 238, 244)
local MUTED = Color3.fromRGB(150, 156, 170)

--- How often the HUD asks for a refresh when nothing has told it to.
---
--- Points move through half a dozen paths -- a lesson, a collection, an ad, a
--- purchase, an achievement -- and wiring a push into every one of them is six
--- chances to miss one and leave a stale number on screen. A poll is one place
--- that cannot be forgotten. Twelve seconds is slow enough to be free and fast
--- enough that a player who just earned something sees it before wondering.
local POLL_SECONDS = 12

local toolbar: Frame
local pointsLabel: TextLabel
local gradeLabel: TextLabel
local barFill: Frame
local streakLabel: TextLabel
local boostLabel: TextLabel

--- Panels that have registered themselves, so opening one closes the rest.
local panels: { [string]: { frame: Frame, onOpen: (() -> ())? } } = {}
local order = 0

local function corner(instance: Instance, radius: number)
	local ui = Instance.new("UICorner")
	ui.CornerRadius = UDim.new(0, radius)
	ui.Parent = instance
end

--- Registers a panel and returns its toolbar button.
---
--- Panels call this instead of building their own button, which is what makes
--- "only one open at a time" true by construction rather than by every panel
--- remembering to close the others.
function HudController.register(id: string, label: string, frame: Frame, onOpen: (() -> ())?)
	panels[id] = { frame = frame, onOpen = onOpen }
	order += 1

	local button = Instance.new("TextButton")
	button.Name = id
	button.Size = UDim2.fromOffset(126, 34)
	button.BackgroundColor3 = ACCENT
	button.BorderSizePixel = 0
	button.Font = Enum.Font.GothamBold
	button.TextSize = 15
	button.TextColor3 = TEXT
	button.Text = label
	button.LayoutOrder = order
	button.Parent = toolbar
	corner(button, 8)

	button.Activated:Connect(function()
		local opening = not frame.Visible
		for otherId, other in panels do
			if otherId ~= id then
				other.frame.Visible = false
			end
		end
		frame.Visible = opening
		if opening and onOpen ~= nil then
			onOpen()
		end
	end)

	return button
end

local function labelIn(parent: Instance, size: number, colour: Color3, y: number, font: Enum.Font)
	local item = Instance.new("TextLabel")
	item.Size = UDim2.new(1, -20, 0, size + 6)
	item.Position = UDim2.fromOffset(12, y)
	item.BackgroundTransparency = 1
	item.Font = font
	item.TextSize = size
	item.TextColor3 = colour
	item.TextXAlignment = Enum.TextXAlignment.Left
	item.Text = ""
	item.Parent = parent
	return item
end

local function buildUi()
	local gui = Instance.new("ScreenGui")
	gui.Name = "HudGui"
	gui.ResetOnSpawn = false
	gui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
	-- The Roblox top bar owns the first ~36 pixels, and on a phone with a notch
	-- rather more than that. Insets keep the toolbar clear of both instead of
	-- guessing an offset that is right on one device.
	gui.ScreenInsets = Enum.ScreenInsets.CoreUISafeInsets
	gui.Parent = player:WaitForChild("PlayerGui")

	local card = Instance.new("Frame")
	card.Name = "Readout"
	card.Size = UDim2.fromOffset(226, 108)
	card.Position = UDim2.fromOffset(12, 12)
	card.BackgroundColor3 = PANEL
	card.BackgroundTransparency = 0.12
	card.BorderSizePixel = 0
	card.Parent = gui
	corner(card, 10)

	pointsLabel = labelIn(card, 20, GOLD, 8, Enum.Font.GothamBold)
	gradeLabel = labelIn(card, 14, TEXT, 34, Enum.Font.GothamMedium)

	local barTrack = Instance.new("Frame")
	barTrack.Size = UDim2.new(1, -24, 0, 6)
	barTrack.Position = UDim2.fromOffset(12, 56)
	barTrack.BackgroundColor3 = Color3.fromRGB(52, 56, 68)
	barTrack.BorderSizePixel = 0
	barTrack.Parent = card
	corner(barTrack, 3)

	barFill = Instance.new("Frame")
	barFill.Size = UDim2.fromScale(0, 1)
	barFill.BackgroundColor3 = ACCENT
	barFill.BorderSizePixel = 0
	barFill.Parent = barTrack
	corner(barFill, 3)

	streakLabel = labelIn(card, 13, MUTED, 68, Enum.Font.Gotham)
	boostLabel = labelIn(card, 13, GOLD, 86, Enum.Font.Gotham)

	toolbar = Instance.new("Frame")
	toolbar.Name = "Toolbar"
	toolbar.Size = UDim2.fromOffset(700, 34)
	toolbar.Position = UDim2.fromOffset(250, 12)
	toolbar.BackgroundTransparency = 1
	toolbar.Parent = gui

	local layout = Instance.new("UIListLayout")
	layout.FillDirection = Enum.FillDirection.Horizontal
	layout.Padding = UDim.new(0, 8)
	layout.SortOrder = Enum.SortOrder.LayoutOrder
	layout.Parent = toolbar
end

local function render(payload: any)
	if payload == nil then
		return
	end

	pointsLabel.Text = L.text("shop.balance", payload.points or 0)

	local grade = payload.grade or 1
	local done = payload.lessonsThisGrade or 0
	local needed = payload.lessonsForGrade or 1
	gradeLabel.Text = L.text("common.grade", grade) .. ` · {done}/{needed}`
	barFill.Size = UDim2.fromScale(math.clamp(done / math.max(needed, 1), 0, 1), 1)

	local streak = payload.streak or 0
	streakLabel.Text = if streak > 0 then L.text("achv.streak", streak) else ""

	-- Pending teaching income is shown next to the boosts rather than added to
	-- the balance: it is not spendable until collected, and a number that
	-- included it would be a number the shop then refuses to honour.
	local pending = payload.pendingPayout or 0
	local parts: { string } = {}
	if pending > 0 then
		table.insert(parts, L.text("hud.pending", pending))
	end
	local count = 0
	for _ in payload.boosts or {} do
		count += 1
	end
	if count > 0 then
		table.insert(parts, L.text("hud.boosts", count))
	end
	boostLabel.Text = table.concat(parts, " · ")
end

function HudController.refresh()
	Remotes.event(Remotes.Names.ClassAction):FireServer({ action = "me" })
end

function HudController.init()
	buildUi()

	Remotes.event(Remotes.Names.ClassResult).OnClientEvent:Connect(function(result: any)
		if result.action == "me" and result.ok then
			render(result.payload)
		end
	end)

	-- Anything that plainly changes the readout refreshes it immediately, so the
	-- poll is a backstop rather than the mechanism.
	Remotes.event(Remotes.Names.StreakState).OnClientEvent:Connect(HudController.refresh)
	Remotes.event(Remotes.Names.AchievementUnlocked).OnClientEvent:Connect(HudController.refresh)
	Remotes.event(Remotes.Names.LessonFinished).OnClientEvent:Connect(HudController.refresh)
	Remotes.event(Remotes.Names.CourseFinished).OnClientEvent:Connect(HudController.refresh)

	task.spawn(function()
		while true do
			HudController.refresh()
			task.wait(POLL_SECONDS)
		end
	end)
end

return HudController
