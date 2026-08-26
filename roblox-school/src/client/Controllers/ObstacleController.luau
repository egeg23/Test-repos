--!strict
--- Heads-up display for an obstacle run.
---
--- Purely a readout. Checkpoints, falls, hazards and the clock are all decided on
--- the server; this shows what it decided. Nothing here can be lied to usefully,
--- because nothing here is asked.

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local Remotes = require(ReplicatedStorage.Shared.Remotes)

local ObstacleController = {}

local player = Players.LocalPlayer

local PANEL = Color3.fromRGB(28, 30, 38)
local TEXT = Color3.fromRGB(236, 238, 244)
local MUTED = Color3.fromRGB(150, 156, 170)
local WARN = Color3.fromRGB(214, 154, 70)

local frame: Frame
local titleLabel: TextLabel
local progressLabel: TextLabel
local timerLabel: TextLabel
local noticeLabel: TextLabel

local deadline: number? = nil
local tick: RBXScriptConnection? = nil

local function label(parent: Instance, size: number, colour: Color3, y: number, font: Enum.Font)
	local text = Instance.new("TextLabel")
	text.Size = UDim2.new(1, -20, 0, size + 6)
	text.Position = UDim2.new(0, 10, 0, y)
	text.BackgroundTransparency = 1
	text.Font = font
	text.TextSize = size
	text.TextColor3 = colour
	text.TextXAlignment = Enum.TextXAlignment.Left
	text.Text = ""
	text.Parent = parent
	return text
end

local function buildUi()
	local gui = Instance.new("ScreenGui")
	gui.Name = "CourseGui"
	gui.ResetOnSpawn = false
	gui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
	gui.Parent = player:WaitForChild("PlayerGui")

	frame = Instance.new("Frame")
	frame.Size = UDim2.fromOffset(280, 118)
	frame.Position = UDim2.new(1, -300, 0, 16)
	frame.BackgroundColor3 = PANEL
	frame.BackgroundTransparency = 0.1
	frame.BorderSizePixel = 0
	frame.Visible = false
	frame.Parent = gui

	local corner = Instance.new("UICorner")
	corner.CornerRadius = UDim.new(0, 10)
	corner.Parent = frame

	titleLabel = label(frame, 16, TEXT, 8, Enum.Font.GothamBold)
	progressLabel = label(frame, 15, MUTED, 34, Enum.Font.GothamMedium)
	timerLabel = label(frame, 22, TEXT, 56, Enum.Font.GothamBold)
	noticeLabel = label(frame, 13, WARN, 88, Enum.Font.Gotham)
end

local function stopTimer()
	if tick ~= nil then
		tick:Disconnect()
		tick = nil
	end
	deadline = nil
end

local function startTimer(seconds: number)
	stopTimer()
	deadline = os.clock() + seconds
	tick = RunService.RenderStepped:Connect(function()
		local target = deadline
		if target == nil then
			return
		end
		local remaining = math.max(0, target - os.clock())
		timerLabel.Text = string.format("%d:%02d", remaining // 60, remaining % 60)
		timerLabel.TextColor3 = if remaining < 15 then WARN else TEXT
	end)
end

local REASONS: { [string]: string } = {
	fell = "Сорвался. Обратно на чекпоинт.",
	hazard = "Задел препятствие.",
	timeLimit = "Время вышло.",
	impossibleSpeed = "Прохождение не засчитано.",
}

function ObstacleController.init()
	buildUi()

	Remotes.event(Remotes.Names.CourseState).OnClientEvent:Connect(function(payload: any)
		if payload.event == "start" then
			frame.Visible = true
			titleLabel.Text = `{payload.title} · {payload.grade} класс`
			noticeLabel.Text = ""
			startTimer(payload.timeLimitSeconds)
		elseif payload.event == "reset" then
			noticeLabel.Text = REASONS[payload.reason] or ""
		elseif payload.event == "checkpoint" then
			noticeLabel.Text = ""
		end
		progressLabel.Text = `Чекпоинты: {payload.reached} из {payload.total}`
	end)

	Remotes.event(Remotes.Names.CourseFinished).OnClientEvent:Connect(function(payload: any)
		stopTimer()
		titleLabel.Text = if payload.passed then "Полоса пройдена" else "Полоса не пройдена"
		progressLabel.Text =
			`{payload.reached} из {payload.total} · +{payload.pointsAwarded} баллов`
		timerLabel.Text = ""
		noticeLabel.Text = if payload.passed
			then ""
			else (REASONS[payload.reason] or "")
		task.delay(6, function()
			frame.Visible = false
		end)
	end)
end

return ObstacleController
