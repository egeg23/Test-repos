--!strict
--- The first three minutes.
---
--- A player arrives on a path outside a building they have never seen, with a
--- toolbar of four panels and no reason to press any of them. The design has
--- always said "a three-minute first lesson that explains the loop"; nothing
--- built it, and the funnel step in AnalyticsService that measures whether
--- anyone reaches their first lesson has been measuring a thing the game never
--- helped anyone do.
---
--- It is a checklist, not a cutscene. Four steps, each one a sentence and an
--- arrow, each completed by doing the actual thing rather than by clicking
--- through. It disappears for good once the loop has been round once, and
--- because completion is derived from profile state rather than from a "seen it"
--- flag, a player who leaves halfway resumes where they were instead of starting
--- again or losing it entirely.

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local TweenService = game:GetService("TweenService")

local Remotes = require(ReplicatedStorage.Shared.Remotes)
local L = require(script.Parent.Parent.Locale)

local OnboardingController = {}

local player = Players.LocalPlayer

local PANEL = Color3.fromRGB(28, 30, 38)
local ACCENT = Color3.fromRGB(70, 96, 190)
local DONE = Color3.fromRGB(64, 160, 92)
local TEXT = Color3.fromRGB(236, 238, 244)
local MUTED = Color3.fromRGB(150, 156, 170)

--- The steps, in order, each with the condition that completes it.
---
--- Conditions read the same `me` payload the HUD does, so onboarding cannot
--- disagree with the rest of the interface about what the player has done -- and
--- there is no separate progress to persist, lose, or get stuck on.
type Step = { key: string, done: (any) -> boolean }

local STEPS: { Step } = {
	{ key = "onboard.enter", done = function(me: any)
		return (me.lessonsThisGrade or 0) > 0 or (me.points or 0) > 0
	end },
	{ key = "onboard.lesson", done = function(me: any)
		return (me.lessonsThisGrade or 0) > 0
	end },
	{ key = "onboard.class", done = function(me: any)
		return me.enrolled == true
	end },
	{ key = "onboard.shop", done = function(me: any)
		return (me.points or 0) >= 100
	end },
}

local card: Frame
local rows: { { frame: Frame, tick: TextLabel, text: TextLabel } } = {}
local finished = false

local function corner(instance: Instance, radius: number)
	local ui = Instance.new("UICorner")
	ui.CornerRadius = UDim.new(0, radius)
	ui.Parent = instance
end

local function buildUi()
	local gui = Instance.new("ScreenGui")
	gui.Name = "OnboardingGui"
	gui.ResetOnSpawn = false
	gui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
	gui.ScreenInsets = Enum.ScreenInsets.CoreUISafeInsets
	gui.Parent = player:WaitForChild("PlayerGui")

	card = Instance.new("Frame")
	card.Name = "FirstSteps"
	card.Size = UDim2.fromOffset(300, 46 + #STEPS * 26)
	-- Bottom left: out of the way of the HUD above and the lesson panel in the
	-- middle, and the corner a player's eye goes to when nothing is happening.
	card.Position = UDim2.new(0, 12, 1, -(58 + #STEPS * 26))
	card.BackgroundColor3 = PANEL
	card.BackgroundTransparency = 0.1
	card.BorderSizePixel = 0
	card.Visible = false
	card.Parent = gui
	corner(card, 10)

	local heading = Instance.new("TextLabel")
	heading.Size = UDim2.new(1, -24, 0, 22)
	heading.Position = UDim2.fromOffset(12, 10)
	heading.BackgroundTransparency = 1
	heading.Font = Enum.Font.GothamBold
	heading.TextSize = 15
	heading.TextColor3 = TEXT
	heading.TextXAlignment = Enum.TextXAlignment.Left
	heading.Text = L.text("onboard.title")
	heading.Parent = card

	for index, step in STEPS do
		local row = Instance.new("Frame")
		row.Size = UDim2.new(1, -24, 0, 24)
		row.Position = UDim2.fromOffset(12, 34 + (index - 1) * 26)
		row.BackgroundTransparency = 1
		row.Parent = card

		local tick = Instance.new("TextLabel")
		tick.Size = UDim2.fromOffset(18, 24)
		tick.BackgroundTransparency = 1
		tick.Font = Enum.Font.GothamBold
		tick.TextSize = 15
		tick.TextColor3 = MUTED
		-- A dot for pending, a tick for done. Symbols rather than words, so the
		-- one column that is not translated is also the one that needs no
		-- translation.
		tick.Text = "•"
		tick.Parent = row

		local text = Instance.new("TextLabel")
		text.Size = UDim2.new(1, -24, 1, 0)
		text.Position = UDim2.fromOffset(22, 0)
		text.BackgroundTransparency = 1
		text.Font = Enum.Font.Gotham
		text.TextSize = 14
		text.TextColor3 = TEXT
		text.TextXAlignment = Enum.TextXAlignment.Left
		text.TextTruncate = Enum.TextTruncate.AtEnd
		text.Text = L.text(step.key)
		text.Parent = row

		table.insert(rows, { frame = row, tick = tick, text = text })
	end
end

local function render(me: any)
	if finished or me == nil then
		return
	end

	local allDone = true
	for index, step in STEPS do
		local row = rows[index]
		local complete = step.done(me)
		row.tick.Text = if complete then "✓" else "•"
		row.tick.TextColor3 = if complete then DONE else ACCENT
		row.text.TextColor3 = if complete then MUTED else TEXT
		row.text.TextTransparency = if complete then 0.35 else 0
		if not complete then
			allDone = false
		end
	end

	if allDone then
		-- Gone for good, and gone gently: a card that vanishes mid-glance reads
		-- as a bug. Nothing is persisted, because the same profile state that
		-- completed it will complete it again on the next join.
		finished = true
		local fade = TweenService:Create(
			card,
			TweenInfo.new(0.5, Enum.EasingStyle.Quad, Enum.EasingDirection.In),
			{ BackgroundTransparency = 1 }
		)
		for _, row in rows do
			TweenService:Create(row.text, TweenInfo.new(0.5), { TextTransparency = 1 }):Play()
			TweenService:Create(row.tick, TweenInfo.new(0.5), { TextTransparency = 1 }):Play()
		end
		fade:Play()
		fade.Completed:Wait()
		card.Visible = false
		return
	end

	card.Visible = true
end

function OnboardingController.init()
	buildUi()

	Remotes.event(Remotes.Names.ClassResult).OnClientEvent:Connect(function(result: any)
		if result.action == "me" and result.ok then
			render(result.payload)
		end
	end)
end

return OnboardingController
