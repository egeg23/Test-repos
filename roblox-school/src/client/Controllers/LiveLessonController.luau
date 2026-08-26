--!strict
--- Live lesson: the invitation, the student's view, and the teacher's controls.
---
--- Deliberately a separate surface from the asynchronous lesson. The pacing is
--- someone else's: a question appears when the teacher sends it and the answer is
--- revealed when they decide, so there is no "next" button on the student side
--- and no timer pretending otherwise.

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Remotes = require(ReplicatedStorage.Shared.Remotes)

local LiveLessonController = {}

local player = Players.LocalPlayer

local PANEL = Color3.fromRGB(28, 30, 38)
local ROW = Color3.fromRGB(52, 56, 66)
local ACCENT = Color3.fromRGB(70, 96, 190)
local CORRECT = Color3.fromRGB(64, 160, 92)
local TEXT = Color3.fromRGB(236, 238, 244)
local MUTED = Color3.fromRGB(150, 156, 170)

local invite: Frame
local inviteLabel: TextLabel
local stage: Frame
local stageTitle: TextLabel
local stageBody: TextLabel
local optionButtons: { TextButton } = {}
local teacherBar: Frame
local teacherLabel: TextLabel

local sessionId: string? = nil
local pendingInvite: string? = nil
local answered = false

local function corner(instance: Instance, radius: number)
	local ui = Instance.new("UICorner")
	ui.CornerRadius = UDim.new(0, radius)
	ui.Parent = instance
end

local function send(action: string, fields: { [string]: any }?)
	local message: { [string]: any } = fields or {}
	message.action = action
	Remotes.event(Remotes.Names.LiveAction):FireServer(message)
end

local function setOptionsEnabled(enabled: boolean)
	for _, button in optionButtons do
		button.Active = enabled
		button.AutoButtonColor = enabled
	end
end

local function showQuestion(payload: any)
	answered = false
	stage.Visible = true
	stageTitle.Text = `Вопрос {payload.position} из {payload.total}`
	stageBody.Text = payload.stem
	for index, button in optionButtons do
		local text = payload.options[index]
		button.Visible = text ~= nil
		button.Text = text or ""
		button.BackgroundColor3 = ROW
	end
	setOptionsEnabled(true)
end

local function buildUi()
	local gui = Instance.new("ScreenGui")
	gui.Name = "LiveLessonGui"
	gui.ResetOnSpawn = false
	gui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
	gui.Parent = player:WaitForChild("PlayerGui")

	invite = Instance.new("Frame")
	invite.Size = UDim2.fromOffset(320, 84)
	invite.Position = UDim2.new(0.5, -160, 0, 16)
	invite.BackgroundColor3 = PANEL
	invite.BorderSizePixel = 0
	invite.Visible = false
	invite.Parent = gui
	corner(invite, 10)

	inviteLabel = Instance.new("TextLabel")
	inviteLabel.Size = UDim2.new(1, -20, 0, 44)
	inviteLabel.Position = UDim2.fromOffset(10, 8)
	inviteLabel.BackgroundTransparency = 1
	inviteLabel.Font = Enum.Font.GothamMedium
	inviteLabel.TextSize = 14
	inviteLabel.TextColor3 = TEXT
	inviteLabel.TextWrapped = true
	inviteLabel.Text = ""
	inviteLabel.Parent = invite

	local accept = Instance.new("TextButton")
	accept.Size = UDim2.fromOffset(140, 26)
	accept.Position = UDim2.fromOffset(10, 50)
	accept.BackgroundColor3 = ACCENT
	accept.BorderSizePixel = 0
	accept.Font = Enum.Font.GothamBold
	accept.TextSize = 14
	accept.TextColor3 = TEXT
	accept.Text = "Зайти на урок"
	accept.Parent = invite
	corner(accept, 6)
	accept.Activated:Connect(function()
		local target = pendingInvite
		if target ~= nil then
			send("join", { sessionId = target })
		end
		invite.Visible = false
	end)

	local decline = Instance.new("TextButton")
	decline.Size = UDim2.fromOffset(140, 26)
	decline.Position = UDim2.fromOffset(160, 50)
	decline.BackgroundColor3 = ROW
	decline.BorderSizePixel = 0
	decline.Font = Enum.Font.Gotham
	decline.TextSize = 14
	decline.TextColor3 = MUTED
	decline.Text = "Не сейчас"
	decline.Parent = invite
	corner(decline, 6)
	decline.Activated:Connect(function()
		pendingInvite = nil
		invite.Visible = false
	end)

	stage = Instance.new("Frame")
	stage.Size = UDim2.fromScale(0.58, 0.6)
	stage.Position = UDim2.fromScale(0.21, 0.2)
	stage.BackgroundColor3 = PANEL
	stage.BorderSizePixel = 0
	stage.Visible = false
	stage.Parent = gui
	corner(stage, 12)

	stageTitle = Instance.new("TextLabel")
	stageTitle.Size = UDim2.new(1, -24, 0, 22)
	stageTitle.Position = UDim2.fromOffset(12, 10)
	stageTitle.BackgroundTransparency = 1
	stageTitle.Font = Enum.Font.GothamMedium
	stageTitle.TextSize = 15
	stageTitle.TextColor3 = MUTED
	stageTitle.TextXAlignment = Enum.TextXAlignment.Left
	stageTitle.Text = ""
	stageTitle.Parent = stage

	stageBody = Instance.new("TextLabel")
	stageBody.Size = UDim2.new(1, -24, 0, 80)
	stageBody.Position = UDim2.fromOffset(12, 36)
	stageBody.BackgroundTransparency = 1
	stageBody.Font = Enum.Font.GothamBold
	stageBody.TextSize = 22
	stageBody.TextColor3 = TEXT
	stageBody.TextWrapped = true
	stageBody.Text = ""
	stageBody.Parent = stage

	for index = 1, 4 do
		local button = Instance.new("TextButton")
		button.Size = UDim2.new(1, -24, 0, 44)
		button.Position = UDim2.fromOffset(12, 124 + (index - 1) * 50)
		button.BackgroundColor3 = ROW
		button.BorderSizePixel = 0
		button.Font = Enum.Font.GothamMedium
		button.TextSize = 17
		button.TextColor3 = TEXT
		button.TextWrapped = true
		button.Text = ""
		button.Parent = stage
		corner(button, 8)
		button.Activated:Connect(function()
			if answered or sessionId == nil then
				return
			end
			answered = true
			setOptionsEnabled(false)
			button.BackgroundColor3 = ACCENT
			send("answer", { choice = index })
		end)
		optionButtons[index] = button
	end

	teacherBar = Instance.new("Frame")
	teacherBar.Size = UDim2.fromOffset(420, 52)
	teacherBar.Position = UDim2.new(0.5, -210, 1, -70)
	teacherBar.BackgroundColor3 = PANEL
	teacherBar.BorderSizePixel = 0
	teacherBar.Visible = false
	teacherBar.Parent = gui
	corner(teacherBar, 10)

	teacherLabel = Instance.new("TextLabel")
	teacherLabel.Size = UDim2.fromOffset(160, 52)
	teacherLabel.Position = UDim2.fromOffset(12, 0)
	teacherLabel.BackgroundTransparency = 1
	teacherLabel.Font = Enum.Font.GothamMedium
	teacherLabel.TextSize = 13
	teacherLabel.TextColor3 = TEXT
	teacherLabel.TextXAlignment = Enum.TextXAlignment.Left
	teacherLabel.TextWrapped = true
	teacherLabel.Text = ""
	teacherLabel.Parent = teacherBar

	local controls = {
		{ caption = "Показать ответ", action = "reveal", x = 176, colour = ROW },
		{ caption = "Дальше", action = "next", x = 288, colour = ACCENT },
		{ caption = "Стоп", action = "end", x = 360, colour = Color3.fromRGB(120, 62, 62) },
	}
	for _, control in controls do
		local button = Instance.new("TextButton")
		button.Size = UDim2.fromOffset(if control.action == "reveal" then 106 else 66, 32)
		button.Position = UDim2.fromOffset(control.x, 10)
		button.BackgroundColor3 = control.colour
		button.BorderSizePixel = 0
		button.Font = Enum.Font.GothamBold
		button.TextSize = 13
		button.TextColor3 = TEXT
		button.Text = control.caption
		button.Parent = teacherBar
		corner(button, 6)
		button.Activated:Connect(function()
			send(control.action)
		end)
	end
end

local REASONS: { [string]: string } = {
	notOwner = "Это не твой класс",
	notALiveLesson = "Живьём можно вести только тест",
	alreadyLive = "Урок уже идёт",
	notEnrolled = "Ты не в этом классе",
	noSession = "Урок уже закончился",
	alreadyInLesson = "Ты уже на уроке",
	teacherLeft = "Преподаватель вышел",
	teacherEnded = "Преподаватель закончил урок",
}

function LiveLessonController.open(classId: string, lessonId: string)
	send("open", { classId = classId, lessonId = lessonId })
end

function LiveLessonController.init()
	buildUi()

	Remotes.event(Remotes.Names.LiveState).OnClientEvent:Connect(function(payload: any)
		local event = payload.event

		if event == "invite" then
			pendingInvite = payload.sessionId
			inviteLabel.Text =
				`{payload.teacherName} начинает урок «{payload.title}» — {payload.total} вопросов`
			invite.Visible = true
		elseif event == "opened" then
			sessionId = payload.sessionId
			teacherBar.Visible = true
			teacherLabel.Text = `«{payload.title}» · ждём учеников`
		elseif event == "waiting" then
			sessionId = payload.sessionId
			stage.Visible = true
			stageTitle.Text = "Урок вот-вот начнётся"
			stageBody.Text = "Преподаватель сейчас задаст первый вопрос."
			for _, button in optionButtons do
				button.Visible = false
			end
		elseif event == "question" then
			sessionId = payload.sessionId
			showQuestion(payload)
		elseif event == "reveal" then
			local correct = optionButtons[payload.correctPosition]
			if correct ~= nil then
				correct.BackgroundColor3 = CORRECT
			end
			setOptionsEnabled(false)
			stageTitle.Text = payload.explanation or ""
		elseif event == "progress" or event == "revealed" then
			teacherLabel.Text = if event == "revealed"
				then `Ответ показан · вопрос {payload.position}`
				else `Вопрос {payload.position} из {payload.total} · ответили `
					.. `{payload.answered} из {payload.participants}`
		elseif event == "received" then
			stageTitle.Text = "Ответ принят. Ждём остальных."
		elseif event == "finished" then
			stage.Visible = true
			stageTitle.Text = if payload.passed then "Урок сдан" else "Урок не сдан"
			stageBody.Text = `Верно {payload.correctCount} из {payload.total}\n`
				.. `+{payload.pointsAwarded} баллов, из них {payload.liveBonus} за живой урок`
			for _, button in optionButtons do
				button.Visible = false
			end
			sessionId = nil
			task.delay(8, function()
				if sessionId == nil then
					stage.Visible = false
				end
			end)
		elseif event == "ended" then
			sessionId = nil
			teacherBar.Visible = false
			stage.Visible = false
			invite.Visible = false
		elseif event == "rejected" then
			warn(`[school] live lesson: {REASONS[payload.reason] or payload.reason}`)
		end
	end)
end

return LiveLessonController
