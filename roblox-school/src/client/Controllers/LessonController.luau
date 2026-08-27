--!strict
--- Lesson UI.
---
--- The server does not wait for this client between questions: it sends the
--- result and the next question back to back. That is deliberate -- a client that
--- has to be waited on is a client that can stall the server. So the next
--- question is queued here and shown once the player has read the explanation.
---
--- All text comes from the shared Strings table, keyed by the player's locale.

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Remotes = require(ReplicatedStorage.Shared.Remotes)
local L = require(script.Parent.Parent.Locale)

local LessonController = {}

local player = Players.LocalPlayer

local CORRECT_COLOUR = Color3.fromRGB(64, 160, 92)
local WRONG_COLOUR = Color3.fromRGB(184, 70, 70)
local IDLE_COLOUR = Color3.fromRGB(52, 56, 66)
local STRUCK_COLOUR = Color3.fromRGB(38, 40, 48)
local HINT_COLOUR = Color3.fromRGB(206, 166, 78)
local PANEL_COLOUR = Color3.fromRGB(28, 30, 38)

type Pending = {
	token: string,
	position: number,
	total: number,
	stem: string,
	options: { string },
	--- Option positions a hint has already struck out. Sent with the question as
	--- well as with the hint, so re-showing a question after an explanation does
	--- not silently restore the options the student paid to remove.
	removed: { number }?,
	hintsLeft: number?,
}

local currentToken: string? = nil
local currentPosition = 0
local queued: Pending? = nil

local optionButtons: { TextButton } = {}
local stemLabel: TextLabel
local progressLabel: TextLabel
local explanationLabel: TextLabel
local continueButton: TextButton
local hintButton: TextButton?
local panel: Frame

--- Whether this player owns the hint pass, from the server's `me` reply. The
--- server checks it again on every hint; this only decides whether to draw a
--- button that would otherwise always refuse.
local hasHintPass = false

local function buildUi()
	local gui = Instance.new("ScreenGui")
	gui.Name = "LessonGui"
	gui.ResetOnSpawn = false
	gui.Enabled = false
	gui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
	gui.Parent = player:WaitForChild("PlayerGui")

	panel = Instance.new("Frame")
	panel.Size = UDim2.fromScale(0.62, 0.7)
	panel.Position = UDim2.fromScale(0.19, 0.15)
	panel.BackgroundColor3 = PANEL_COLOUR
	panel.BorderSizePixel = 0
	panel.Parent = gui

	local corner = Instance.new("UICorner")
	corner.CornerRadius = UDim.new(0, 12)
	corner.Parent = panel

	local layout = Instance.new("UIListLayout")
	layout.Padding = UDim.new(0, 10)
	layout.SortOrder = Enum.SortOrder.LayoutOrder
	layout.HorizontalAlignment = Enum.HorizontalAlignment.Center
	layout.Parent = panel

	local padding = Instance.new("UIPadding")
	padding.PaddingTop = UDim.new(0, 16)
	padding.PaddingBottom = UDim.new(0, 16)
	padding.PaddingLeft = UDim.new(0, 16)
	padding.PaddingRight = UDim.new(0, 16)
	padding.Parent = panel

	progressLabel = Instance.new("TextLabel")
	progressLabel.Size = UDim2.new(1, 0, 0, 22)
	progressLabel.BackgroundTransparency = 1
	progressLabel.Font = Enum.Font.GothamMedium
	progressLabel.TextSize = 16
	progressLabel.TextColor3 = Color3.fromRGB(150, 156, 170)
	progressLabel.Text = ""
	progressLabel.LayoutOrder = 1
	progressLabel.Parent = panel

	stemLabel = Instance.new("TextLabel")
	stemLabel.Size = UDim2.new(1, 0, 0, 80)
	stemLabel.BackgroundTransparency = 1
	stemLabel.Font = Enum.Font.GothamBold
	stemLabel.TextSize = 24
	stemLabel.TextColor3 = Color3.fromRGB(240, 242, 248)
	stemLabel.TextWrapped = true
	stemLabel.Text = ""
	stemLabel.LayoutOrder = 2
	stemLabel.Parent = panel

	for index = 1, 4 do
		local button = Instance.new("TextButton")
		button.Size = UDim2.new(1, 0, 0, 46)
		button.BackgroundColor3 = IDLE_COLOUR
		button.BorderSizePixel = 0
		button.Font = Enum.Font.GothamMedium
		button.TextSize = 18
		button.TextColor3 = Color3.fromRGB(236, 238, 244)
		button.TextWrapped = true
		button.Text = ""
		button.LayoutOrder = 2 + index
		button.Parent = panel

		local buttonCorner = Instance.new("UICorner")
		buttonCorner.CornerRadius = UDim.new(0, 8)
		buttonCorner.Parent = button

		button.Activated:Connect(function()
			LessonController.choose(index)
		end)
		optionButtons[index] = button
	end

	explanationLabel = Instance.new("TextLabel")
	explanationLabel.Size = UDim2.new(1, 0, 0, 56)
	explanationLabel.BackgroundTransparency = 1
	explanationLabel.Font = Enum.Font.Gotham
	explanationLabel.TextSize = 16
	explanationLabel.TextColor3 = Color3.fromRGB(190, 196, 210)
	explanationLabel.TextWrapped = true
	explanationLabel.Text = ""
	explanationLabel.Visible = false
	explanationLabel.LayoutOrder = 7
	explanationLabel.Parent = panel

	continueButton = Instance.new("TextButton")
	continueButton.Size = UDim2.new(0.4, 0, 0, 40)
	continueButton.BackgroundColor3 = Color3.fromRGB(70, 96, 190)
	continueButton.BorderSizePixel = 0
	continueButton.Font = Enum.Font.GothamBold
	continueButton.TextSize = 18
	continueButton.TextColor3 = Color3.fromRGB(255, 255, 255)
	continueButton.Text = L.text("common.next")
	continueButton.Visible = false
	continueButton.LayoutOrder = 8
	continueButton.Parent = panel

	local hint = Instance.new("TextButton")
	hint.Name = "Hint"
	hint.Size = UDim2.fromOffset(150, 30)
	hint.Position = UDim2.new(0, 16, 1, -44)
	hint.BackgroundColor3 = HINT_COLOUR
	hint.BorderSizePixel = 0
	hint.Font = Enum.Font.GothamBold
	hint.TextSize = 14
	hint.TextColor3 = PANEL_COLOUR
	hint.Text = ""
	hint.Visible = false
	hint.Parent = panel
	hint.Activated:Connect(function()
		Remotes.event(Remotes.Names.UseHint):FireServer()
	end)
	hintButton = hint

	local continueCorner = Instance.new("UICorner")
	continueCorner.CornerRadius = UDim.new(0, 8)
	continueCorner.Parent = continueButton

	continueButton.Activated:Connect(function()
		LessonController.advance()
	end)

	return gui
end

local screenGui: ScreenGui

local function setOptionsEnabled(enabled: boolean)
	for _, button in optionButtons do
		button.Active = enabled
		button.AutoButtonColor = enabled
	end
end

--- The hint button only exists for a player who owns the pass and has hints
--- left. Hidden rather than disabled: an always-visible button that always
--- refuses is an advert dressed as a control.
local function updateHintButton(hintsLeft: number?)
	if hintButton == nil then
		return
	end
	local left = hintsLeft or 0
	hintButton.Visible = hasHintPass and left > 0
	hintButton.Text = L.text("lesson.hint", left)
end

local function show(pending: Pending)
	currentToken = pending.token
	currentPosition = pending.position

	progressLabel.Text = L.text("lesson.progress", pending.position, pending.total)
	stemLabel.Text = pending.stem
	explanationLabel.Visible = false
	continueButton.Visible = false

	local removed = pending.removed or {}
	for index, button in optionButtons do
		local text = pending.options[index]
		button.Visible = text ~= nil
		button.Text = text or ""
		-- Struck out rather than hidden: a vanishing option makes the remaining
		-- ones jump, and a student who just spent a hint should see what it
		-- bought them.
		local struck = table.find(removed, index) ~= nil
		button.BackgroundColor3 = if struck then STRUCK_COLOUR else IDLE_COLOUR
		button.TextTransparency = if struck then 0.55 else 0
		button.Active = not struck
	end

	updateHintButton(pending.hintsLeft)
	setOptionsEnabled(true)
	screenGui.Enabled = true
end

function LessonController.choose(index: number)
	if currentToken == nil then
		return
	end
	local button = optionButtons[index]
	if button == nil or not button.Visible or not button.Active then
		return
	end

	setOptionsEnabled(false)
	Remotes.event(Remotes.Names.SubmitAnswer):FireServer({
		token = currentToken,
		position = currentPosition,
		choice = index,
	})
end

function LessonController.advance()
	continueButton.Visible = false
	explanationLabel.Visible = false

	local next = queued
	queued = nil
	if next ~= nil then
		show(next)
	else
		screenGui.Enabled = false
		currentToken = nil
	end
end

function LessonController.start(subject: string)
	Remotes.event(Remotes.Names.StartLesson):FireServer({ subject = subject })
end

--- A lesson a teacher assembled, taken inside their class.
function LessonController.startClassLesson(classId: string, lessonId: string)
	Remotes.event(Remotes.Names.StartLesson):FireServer({
		classId = classId,
		lessonId = lessonId,
	})
end

function LessonController.init()
	screenGui = buildUi()

	Remotes.event(Remotes.Names.LessonQuestion).OnClientEvent:Connect(function(payload: any)
		if currentToken ~= nil and continueButton.Visible then
			-- Mid-explanation: hold it until the player has read the last one.
			queued = payload
			return
		end
		show(payload)
	end)

	Remotes.event(Remotes.Names.AnswerResult).OnClientEvent:Connect(function(payload: any)
		local chosenCorrect = payload.correct == true
		local correctButton = optionButtons[payload.correctPosition]
		if correctButton ~= nil then
			correctButton.BackgroundColor3 = CORRECT_COLOUR
		end
		if not chosenCorrect then
			for _, button in optionButtons do
				if button.BackgroundColor3 ~= CORRECT_COLOUR and not button.Active then
					button.BackgroundColor3 = WRONG_COLOUR
					break
				end
			end
		end

		explanationLabel.Text = payload.explanation or ""
		explanationLabel.Visible = explanationLabel.Text ~= ""
		continueButton.Visible = true
	end)

	Remotes.event(Remotes.Names.LessonFinished).OnClientEvent:Connect(function(payload: any)
		-- Assembly results come down this same remote and carry an answer key.
		-- They belong to AssemblyController; reacting here would paint a quiz
		-- verdict over a task this panel was never showing.
		if payload.answers ~= nil then
			return
		end
		queued = nil
		progressLabel.Text = L.text(if payload.passed then "lesson.passed" else "lesson.failed")
		stemLabel.Text = L.text(
			"lesson.score",
			payload.correctCount,
			payload.total,
			payload.pointsAwarded
		)
		for _, button in optionButtons do
			button.Visible = false
		end
		explanationLabel.Text = if payload.graduated
			then L.text("lesson.graduated")
			elseif payload.advanced then L.text("lesson.advanced", payload.grade)
			else ""
		explanationLabel.Visible = explanationLabel.Text ~= ""
		continueButton.Visible = true
		currentToken = nil
	end)

	Remotes.event(Remotes.Names.LessonHint).OnClientEvent:Connect(function(payload: any)
		if payload.token ~= currentToken or payload.position ~= currentPosition then
			return
		end
		local removed = payload.removed or {}
		for index, button in optionButtons do
			if table.find(removed, index) ~= nil then
				button.BackgroundColor3 = STRUCK_COLOUR
				button.TextTransparency = 0.55
				button.Active = false
			end
		end
		updateHintButton(payload.hintsLeft)
	end)

	Remotes.event(Remotes.Names.ClassResult).OnClientEvent:Connect(function(result: any)
		if result.action == "me" and result.ok then
			local passes = result.payload.passes
			hasHintPass = typeof(passes) == "table" and passes.hint == true
		end
	end)

	Remotes.event(Remotes.Names.LessonRejected).OnClientEvent:Connect(function(reason: any)
		warn(`[school] lesson rejected: {reason}`)
	end)
end

return LessonController
