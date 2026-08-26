--!strict
--- Lesson UI.
---
--- The server does not wait for this client between questions: it sends the
--- result and the next question back to back. That is deliberate -- a client that
--- has to be waited on is a client that can stall the server. So the next
--- question is queued here and shown once the player has read the explanation.
---
--- Strings are hardcoded Russian for now. They move into a LocalizationTable
--- keyed by the `displayKey` fields in config when the locale work lands.

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Remotes = require(ReplicatedStorage.Shared.Remotes)

local LessonController = {}

local player = Players.LocalPlayer

local CORRECT_COLOUR = Color3.fromRGB(64, 160, 92)
local WRONG_COLOUR = Color3.fromRGB(184, 70, 70)
local IDLE_COLOUR = Color3.fromRGB(52, 56, 66)
local PANEL_COLOUR = Color3.fromRGB(28, 30, 38)

type Pending = { token: string, position: number, total: number, stem: string, options: { string } }

local currentToken: string? = nil
local currentPosition = 0
local queued: Pending? = nil

local optionButtons: { TextButton } = {}
local stemLabel: TextLabel
local progressLabel: TextLabel
local explanationLabel: TextLabel
local continueButton: TextButton
local panel: Frame

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
	continueButton.Text = "Дальше"
	continueButton.Visible = false
	continueButton.LayoutOrder = 8
	continueButton.Parent = panel

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

local function show(pending: Pending)
	currentToken = pending.token
	currentPosition = pending.position

	progressLabel.Text = `Вопрос {pending.position} из {pending.total}`
	stemLabel.Text = pending.stem
	explanationLabel.Visible = false
	continueButton.Visible = false

	for index, button in optionButtons do
		local text = pending.options[index]
		button.Visible = text ~= nil
		button.Text = text or ""
		button.BackgroundColor3 = IDLE_COLOUR
	end

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
		local verdict = if payload.passed then "Урок сдан" else "Урок не сдан"
		progressLabel.Text = verdict
		stemLabel.Text =
			`Верных ответов: {payload.correctCount} из {payload.total}\n+{payload.pointsAwarded} баллов`
		for _, button in optionButtons do
			button.Visible = false
		end
		explanationLabel.Text = if payload.graduated
			then "Все классы пройдены. Открой «Школа» и выбери, что дальше."
			elseif payload.advanced then `Ты перешёл в {payload.grade} класс`
			else ""
		explanationLabel.Visible = explanationLabel.Text ~= ""
		continueButton.Visible = true
		currentToken = nil
	end)

	Remotes.event(Remotes.Names.LessonRejected).OnClientEvent:Connect(function(reason: any)
		warn(`[school] lesson rejected: {reason}`)
	end)
end

return LessonController
