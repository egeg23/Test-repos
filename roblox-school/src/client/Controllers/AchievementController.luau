--!strict
--- The achievement board, and the toast that fires when a tier unlocks.
---
--- Two jobs that belong together because they are the same information at two
--- speeds. The toast is what makes a perk feel earned in the moment; the board is
--- what makes the next one feel reachable. A branch system with only the board is
--- a menu, and one with only the toast is a slot machine.
---
--- The board is drawn from what the server sends and nothing else: the client
--- never decides whether a tier is unlocked, only how to draw the answer.

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local TweenService = game:GetService("TweenService")

local Remotes = require(ReplicatedStorage.Shared.Remotes)
local L = require(script.Parent.Parent.Locale)

local AchievementController = {}

local player = Players.LocalPlayer

local PANEL = Color3.fromRGB(28, 30, 38)
local ROW = Color3.fromRGB(44, 48, 58)
local ACCENT = Color3.fromRGB(70, 96, 190)
local GOLD = Color3.fromRGB(206, 166, 78)
local TEXT = Color3.fromRGB(236, 238, 244)
local MUTED = Color3.fromRGB(150, 156, 170)

local panel: Frame
local listFrame: ScrollingFrame
local streakLabel: TextLabel
local toastHolder: Frame

--- Perk values are read from the payload, so the label has to be built from an
--- effect name the server chose. Multipliers read as x1.08, counts as +3.
local MULTIPLICATIVE: { [string]: boolean } = {
	studentPoints = true,
	teacherPayout = true,
	adReward = true,
}

local function corner(instance: Instance, radius: number)
	local ui = Instance.new("UICorner")
	ui.CornerRadius = UDim.new(0, radius)
	ui.Parent = instance
end

local function perkText(effect: string, value: number): string
	local formatted = if MULTIPLICATIVE[effect]
		then string.format("%.2f", value)
		else tostring(value)
	return L.text(`perk.{effect}`, formatted)
end

local function label(parent: Instance, text: string, size: number, colour: Color3, x: number, y: number)
	local item = Instance.new("TextLabel")
	item.Size = UDim2.new(1, -x - 12, 0, size + 6)
	item.Position = UDim2.fromOffset(x, y)
	item.BackgroundTransparency = 1
	item.Font = Enum.Font.Gotham
	item.TextSize = size
	item.TextColor3 = colour
	item.TextXAlignment = Enum.TextXAlignment.Left
	item.TextTruncate = Enum.TextTruncate.AtEnd
	item.Text = text
	item.Parent = parent
	return item
end

--- One branch: its name, how far along the player is, and a segmented bar with
--- one segment per tier. The bar is the whole point -- a number alone does not
--- say "two more and something happens".
local function renderBranch(branch: any, order: number)
	local unlockedCount = 0
	local nextTier: any = nil
	for _, tier in branch.tiers do
		if tier.unlocked then
			unlockedCount += 1
		elseif nextTier == nil then
			nextTier = tier
		end
	end

	local row = Instance.new("Frame")
	row.Size = UDim2.new(1, 0, 0, 76)
	row.BackgroundColor3 = ROW
	row.BorderSizePixel = 0
	row.LayoutOrder = order
	row.Parent = listFrame
	corner(row, 8)

	local title = label(row, L.text(branch.displayKey), 15, TEXT, 12, 8)
	title.Font = Enum.Font.GothamBold

	if nextTier ~= nil then
		label(row, L.text("achv.progress", branch.value, nextTier.at), 13, MUTED, 12, 30)
		local reward = label(row, perkText(nextTier.effect, nextTier.value), 13, GOLD, 12, 48)
		reward.TextXAlignment = Enum.TextXAlignment.Left
	else
		label(row, L.text("achv.done"), 13, GOLD, 12, 30)
	end

	-- Segments, one per tier, filled up to what is unlocked.
	local segments = #branch.tiers
	local barWidth = 150
	for index = 1, segments do
		local segment = Instance.new("Frame")
		segment.Size = UDim2.fromOffset(barWidth / segments - 3, 6)
		segment.Position = UDim2.new(1, -barWidth - 12 + (index - 1) * (barWidth / segments), 0, 34)
		segment.BackgroundColor3 = if index <= unlockedCount then GOLD else PANEL
		segment.BorderSizePixel = 0
		segment.Parent = row
		corner(segment, 3)
	end

	local count = label(row, `{unlockedCount} / {segments}`, 13, MUTED, 0, 50)
	count.Size = UDim2.new(0, barWidth, 0, 18)
	count.Position = UDim2.new(1, -barWidth - 12, 0, 50)
	count.TextXAlignment = Enum.TextXAlignment.Right
end

local function render(payload: any)
	for _, child in listFrame:GetChildren() do
		if child:IsA("Frame") then
			child:Destroy()
		end
	end
	if payload == nil then
		return
	end

	streakLabel.Text = L.text("achv.streak", payload.streak or 0)

	local order = 0
	for _, branch in payload.branches do
		order += 1
		renderBranch(branch, order)
	end

	-- The perk summary last: it is the answer to "what has all this bought me",
	-- which is a question a player asks after seeing the branches, not before.
	local summary = Instance.new("Frame")
	summary.Size = UDim2.new(1, 0, 0, 26 + 18 * 7)
	summary.BackgroundColor3 = ROW
	summary.BorderSizePixel = 0
	summary.LayoutOrder = order + 1
	summary.Parent = listFrame
	corner(summary, 8)

	local heading = label(summary, L.text("achv.perks"), 14, TEXT, 12, 6)
	heading.Font = Enum.Font.GothamBold

	local y = 28
	for _, effect in
		{
			"studentPoints",
			"teacherPayout",
			"adReward",
			"obstacleTime",
			"classCapacity",
			"lessonSlots",
			"attemptRefund",
		}
	do
		local value = payload.perks[effect]
		if value ~= nil then
			-- An untouched effect is its identity, and printing "x1.00" seven
			-- times is a wall of nothing. Only what has actually changed shows.
			local identity = if MULTIPLICATIVE[effect] then 1 else 0
			if value ~= identity then
				label(summary, perkText(effect, value), 13, MUTED, 12, y)
				y += 18
			end
		end
	end
	summary.Size = UDim2.new(1, 0, 0, math.max(46, y + 6))
end

--- A toast per unlocked tier, stacked. Slides in, waits, fades out.
local function toast(entry: any)
	local card = Instance.new("Frame")
	card.Size = UDim2.fromOffset(280, 54)
	card.BackgroundColor3 = PANEL
	card.BackgroundTransparency = 0.05
	card.BorderSizePixel = 0
	card.Parent = toastHolder
	corner(card, 10)

	local stripe = Instance.new("Frame")
	stripe.Size = UDim2.fromOffset(4, 54)
	stripe.BackgroundColor3 = GOLD
	stripe.BorderSizePixel = 0
	stripe.Parent = card
	corner(stripe, 2)

	local name = label(card, L.text("achv.unlocked", L.text(`achv.{entry.branch}`)), 14, TEXT, 14, 8)
	name.Font = Enum.Font.GothamBold
	label(card, L.text("achv.reward", entry.points), 13, GOLD, 14, 28)

	-- Off-screen to the right, then in. The list layout owns the vertical
	-- position, so only the offset is animated.
	card.Position = UDim2.new(1, 300, 0, 0)
	TweenService
		:Create(card, TweenInfo.new(0.35, Enum.EasingStyle.Quad, Enum.EasingDirection.Out), {
			Position = UDim2.new(0, 0, 0, 0),
		})
		:Play()

	task.delay(4, function()
		local fade = TweenService:Create(
			card,
			TweenInfo.new(0.4, Enum.EasingStyle.Quad, Enum.EasingDirection.In),
			{ Position = UDim2.new(1, 300, 0, 0), BackgroundTransparency = 1 }
		)
		fade:Play()
		fade.Completed:Wait()
		card:Destroy()
	end)
end

local function buildUi()
	local gui = Instance.new("ScreenGui")
	gui.Name = "AchievementGui"
	gui.ResetOnSpawn = false
	gui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
	gui.Parent = player:WaitForChild("PlayerGui")

	local toggle = Instance.new("TextButton")
	toggle.Size = UDim2.fromOffset(130, 36)
	toggle.Position = UDim2.fromOffset(400, 16)
	toggle.BackgroundColor3 = ACCENT
	toggle.BorderSizePixel = 0
	toggle.Font = Enum.Font.GothamBold
	toggle.TextSize = 16
	toggle.TextColor3 = TEXT
	toggle.Text = L.text("achv.title")
	toggle.Parent = gui
	corner(toggle, 8)

	panel = Instance.new("Frame")
	panel.Size = UDim2.fromScale(0.34, 0.7)
	panel.Position = UDim2.fromScale(0.33, 0.14)
	panel.BackgroundColor3 = PANEL
	panel.BorderSizePixel = 0
	panel.Visible = false
	panel.Parent = gui
	corner(panel, 12)

	toggle.Activated:Connect(function()
		panel.Visible = not panel.Visible
		if panel.Visible then
			AchievementController.refresh()
		end
	end)

	streakLabel = Instance.new("TextLabel")
	streakLabel.Size = UDim2.new(1, -24, 0, 26)
	streakLabel.Position = UDim2.fromOffset(12, 12)
	streakLabel.BackgroundTransparency = 1
	streakLabel.Font = Enum.Font.GothamBold
	streakLabel.TextSize = 16
	streakLabel.TextColor3 = GOLD
	streakLabel.TextXAlignment = Enum.TextXAlignment.Left
	streakLabel.Text = ""
	streakLabel.Parent = panel

	listFrame = Instance.new("ScrollingFrame")
	listFrame.Size = UDim2.new(1, -24, 1, -54)
	listFrame.Position = UDim2.fromOffset(12, 44)
	listFrame.BackgroundTransparency = 1
	listFrame.BorderSizePixel = 0
	listFrame.ScrollBarThickness = 5
	listFrame.AutomaticCanvasSize = Enum.AutomaticSize.Y
	listFrame.CanvasSize = UDim2.new()
	listFrame.Parent = panel

	local layout = Instance.new("UIListLayout")
	layout.Padding = UDim.new(0, 6)
	layout.SortOrder = Enum.SortOrder.LayoutOrder
	layout.Parent = listFrame

	-- Toasts live in their own container so they appear whether or not the panel
	-- is open -- which is the only time they matter.
	toastHolder = Instance.new("Frame")
	toastHolder.Size = UDim2.fromOffset(280, 300)
	toastHolder.Position = UDim2.new(1, -300, 0, 150)
	toastHolder.BackgroundTransparency = 1
	toastHolder.Parent = gui

	local toastLayout = Instance.new("UIListLayout")
	toastLayout.Padding = UDim.new(0, 8)
	toastLayout.SortOrder = Enum.SortOrder.LayoutOrder
	toastLayout.Parent = toastHolder
end

function AchievementController.refresh()
	Remotes.event(Remotes.Names.ClassAction):FireServer({ action = "achievements" })
end

function AchievementController.init()
	buildUi()

	Remotes.event(Remotes.Names.ClassResult).OnClientEvent:Connect(function(result: any)
		if result.action == "achievements" and result.ok then
			render(result.payload)
		end
	end)

	Remotes.event(Remotes.Names.AchievementUnlocked).OnClientEvent:Connect(function(granted: any)
		for _, entry in granted do
			toast(entry)
		end
		if panel.Visible then
			AchievementController.refresh()
		end
	end)

	Remotes.event(Remotes.Names.StreakState).OnClientEvent:Connect(function(state: any)
		streakLabel.Text = L.text("achv.streak", state.days or 0)
	end)
end

return AchievementController
