--!strict
--- Campus panel: the election, the director's controls, and a dean's queue.
---
--- Which controls appear is decided by what the server sends back, not by
--- anything this file believes about the player. Every action is re-checked
--- server-side, so hiding a button is a courtesy rather than a permission.

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Campus = require(ReplicatedStorage.Shared.Config.Campus)
local Subjects = require(ReplicatedStorage.Shared.Config.Subjects)
local Remotes = require(ReplicatedStorage.Shared.Remotes)

local CampusController = {}

local player = Players.LocalPlayer

local PANEL = Color3.fromRGB(28, 30, 38)
local ROW = Color3.fromRGB(44, 48, 58)
local ACCENT = Color3.fromRGB(70, 96, 190)
local TEXT = Color3.fromRGB(236, 238, 244)
local MUTED = Color3.fromRGB(150, 156, 170)

local PHASE_NAMES: { [string]: string } = {
	term = "Идёт семестр",
	campaign = "Выдвижение кандидатов",
	voting = "Голосование",
}

local MOTTO_NAMES: { [string]: string } = {
	["motto.learnTogether"] = "Учимся вместе",
	["motto.noOneLeftBehind"] = "Никого не бросаем",
	["motto.askWhy"] = "Спрашивай «почему»",
	["motto.tryAgain"] = "Попробуй ещё раз",
	["motto.knowledgeIsPower"] = "Знание — сила",
	["motto.everyDayCounts"] = "Каждый день важен",
}

local panel: Frame
local headerLabel: TextLabel
local phaseLabel: TextLabel
local listFrame: ScrollingFrame
local statusLabel: TextLabel

local function send(action: string, fields: { [string]: any }?)
	local message: { [string]: any } = fields or {}
	message.action = action
	Remotes.event(Remotes.Names.ClassAction):FireServer(message)
end

local function corner(instance: Instance, radius: number)
	local ui = Instance.new("UICorner")
	ui.CornerRadius = UDim.new(0, radius)
	ui.Parent = instance
end

local function clearList()
	for _, child in listFrame:GetChildren() do
		if child:IsA("GuiObject") then
			child:Destroy()
		end
	end
end

local function row(height: number): Frame
	local element = Instance.new("Frame")
	element.Size = UDim2.new(1, -8, 0, height)
	element.BackgroundColor3 = ROW
	element.BorderSizePixel = 0
	element.Parent = listFrame
	corner(element, 8)
	return element
end

local function text(parent: GuiObject, value: string, size: number, colour: Color3, y: number)
	local label = Instance.new("TextLabel")
	label.Size = UDim2.new(1, -130, 0, size + 6)
	label.Position = UDim2.new(0, 10, 0, y)
	label.BackgroundTransparency = 1
	label.Font = Enum.Font.GothamMedium
	label.TextSize = size
	label.TextColor3 = colour
	label.TextXAlignment = Enum.TextXAlignment.Left
	label.TextTruncate = Enum.TextTruncate.AtEnd
	label.Text = value
	label.Parent = parent
	return label
end

local function action(parent: GuiObject, caption: string, width: number, colour: Color3): TextButton
	local button = Instance.new("TextButton")
	button.Size = UDim2.new(0, width, 0, 30)
	button.Position = UDim2.new(1, -width - 8, 0, 8)
	button.BackgroundColor3 = colour
	button.BorderSizePixel = 0
	button.Font = Enum.Font.GothamBold
	button.TextSize = 14
	button.TextColor3 = TEXT
	button.Text = caption
	button.Parent = parent
	corner(button, 6)
	return button
end

local function render(view: any)
	clearList()

	local remaining = view.cycleDays - view.dayInCycle
	local week = `{view.termIndex + 1} четверть, неделя {view.weekInTerm + 1} из {view.weeksPerTerm}`
	local calendar = if view.isTestWeek then `{week} · контрольная неделя ×1.2` else week
	phaseLabel.Text = `{PHASE_NAMES[view.phase] or view.phase} · {calendar}`

	local head = row(72)
	text(
		head,
		if view.directorUserId > 0
			then `Директор: {view.directorName}`
			else "Директора нет — кампус ждёт выборов",
		16,
		TEXT,
		8
	)
	local extras = {}
	if view.subjectOfMonth ~= nil then
		table.insert(extras, `предмет месяца: {view.subjectOfMonth}`)
	end
	if view.motto ~= nil then
		table.insert(extras, MOTTO_NAMES[view.motto] or view.motto)
	end
	if view.eventUntil > os.time() then
		table.insert(extras, "идёт школьное событие")
	end
	text(
		head,
		if #extras > 0 then table.concat(extras, " · ") else `до конца срока {remaining} дн.`,
		13,
		MUTED,
		34
	)

	if view.phase == "campaign" then
		local stand = row(46)
		text(stand, "Выдвинуть свою кандидатуру", 15, TEXT, 12)
		action(stand, "Выдвинуться", ACCENT, 120).Activated:Connect(function()
			send("nominate")
		end)
	end

	for _, candidate in view.candidates do
		local element = row(46)
		text(element, `{candidate.name} — {math.floor(candidate.votes)} голосов`, 15, TEXT, 12)
		if view.phase == "voting" then
			action(element, "Голос", ACCENT, 90).Activated:Connect(function()
				send("vote", { candidateUserId = candidate.userId })
			end)
		end
	end

	if view.phase ~= "term" and #view.candidates == 0 then
		text(row(40), "Кандидатов пока нет.", 15, MUTED, 10)
	end

	-- The director's own controls. Shown when the server says this player holds
	-- the office; refused server-side regardless.
	if view.directorUserId == player.UserId then
		local eventRow = row(46)
		text(eventRow, `Школьное событие · осталось {view.eventsLeft}`, 15, TEXT, 12)
		action(eventRow, "Запустить", ACCENT, 110).Activated:Connect(function()
			send("startEvent")
		end)

		local subjectRow = row(76)
		text(subjectRow, "Предмет месяца (×1.5 всем)", 15, TEXT, 6)
		local index = 0
		for _, entry in Subjects.List do
			local button = Instance.new("TextButton")
			button.Size = UDim2.fromOffset(76, 26)
			button.Position = UDim2.new(0, 10 + (index % 6) * 82, 0, 34 + math.floor(index / 6) * 30)
			button.BackgroundColor3 = if view.subjectOfMonth == entry.id then ACCENT else PANEL
			button.BorderSizePixel = 0
			button.Font = Enum.Font.Gotham
			button.TextSize = 12
			button.TextColor3 = TEXT
			button.Text = entry.id
			button.Parent = subjectRow
			corner(button, 5)
			button.Activated:Connect(function()
				send("subjectOfMonth", { subject = entry.id })
			end)
			index += 1
		end

		local mottoRow = row(76)
		text(mottoRow, "Девиз школы", 15, TEXT, 6)
		local mottoIndex = 0
		for _, key in Campus.Mottos do
			local button = Instance.new("TextButton")
			button.Size = UDim2.fromOffset(150, 26)
			button.Position =
				UDim2.new(0, 10 + (mottoIndex % 3) * 158, 0, 34 + math.floor(mottoIndex / 3) * 30)
			button.BackgroundColor3 = if view.motto == key then ACCENT else PANEL
			button.BorderSizePixel = 0
			button.Font = Enum.Font.Gotham
			button.TextSize = 12
			button.TextColor3 = TEXT
			button.Text = MOTTO_NAMES[key] or key
			button.Parent = mottoRow
			corner(button, 5)
			button.Activated:Connect(function()
				send("motto", { motto = key })
			end)
			mottoIndex += 1
		end
	end

	local deanNames: { string } = {}
	for subject, name in view.deans do
		table.insert(deanNames, `{subject}: {name}`)
	end
	if #deanNames > 0 then
		text(row(40), `Завучи — {table.concat(deanNames, ", ")}`, 13, MUTED, 12)
	end
end

local function buildUi()
	local gui = Instance.new("ScreenGui")
	gui.Name = "CampusGui"
	gui.ResetOnSpawn = false
	gui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
	gui.Parent = player:WaitForChild("PlayerGui")

	local toggle = Instance.new("TextButton")
	toggle.Size = UDim2.fromOffset(120, 36)
	toggle.Position = UDim2.fromOffset(144, 16)
	toggle.BackgroundColor3 = ACCENT
	toggle.BorderSizePixel = 0
	toggle.Font = Enum.Font.GothamBold
	toggle.TextSize = 16
	toggle.TextColor3 = TEXT
	toggle.Text = "Кампус"
	toggle.Parent = gui
	corner(toggle, 8)

	panel = Instance.new("Frame")
	panel.Size = UDim2.fromScale(0.44, 0.62)
	panel.Position = UDim2.fromScale(0.28, 0.18)
	panel.BackgroundColor3 = PANEL
	panel.BorderSizePixel = 0
	panel.Visible = false
	panel.Parent = gui
	corner(panel, 12)

	toggle.Activated:Connect(function()
		panel.Visible = not panel.Visible
		if panel.Visible then
			send("campus")
		end
	end)

	headerLabel = Instance.new("TextLabel")
	headerLabel.Size = UDim2.new(1, -24, 0, 24)
	headerLabel.Position = UDim2.fromOffset(12, 10)
	headerLabel.BackgroundTransparency = 1
	headerLabel.Font = Enum.Font.GothamBold
	headerLabel.TextSize = 17
	headerLabel.TextColor3 = TEXT
	headerLabel.TextXAlignment = Enum.TextXAlignment.Left
	headerLabel.Text = "Кампус"
	headerLabel.Parent = panel

	phaseLabel = Instance.new("TextLabel")
	phaseLabel.Size = UDim2.new(1, -24, 0, 18)
	phaseLabel.Position = UDim2.fromOffset(12, 34)
	phaseLabel.BackgroundTransparency = 1
	phaseLabel.Font = Enum.Font.Gotham
	phaseLabel.TextSize = 13
	phaseLabel.TextColor3 = MUTED
	phaseLabel.TextXAlignment = Enum.TextXAlignment.Left
	phaseLabel.Text = ""
	phaseLabel.Parent = panel

	listFrame = Instance.new("ScrollingFrame")
	listFrame.Size = UDim2.new(1, -24, 1, -92)
	listFrame.Position = UDim2.fromOffset(12, 58)
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

	statusLabel = Instance.new("TextLabel")
	statusLabel.Size = UDim2.new(1, -24, 0, 24)
	statusLabel.Position = UDim2.new(0, 12, 1, -30)
	statusLabel.BackgroundTransparency = 1
	statusLabel.Font = Enum.Font.Gotham
	statusLabel.TextSize = 13
	statusLabel.TextColor3 = MUTED
	statusLabel.TextXAlignment = Enum.TextXAlignment.Left
	statusLabel.Text = ""
	statusLabel.Parent = panel
end

local REASONS: { [string]: string } = {
	notCampaign = "Выдвигаться можно только в дни выдвижения",
	notVoting = "Голосование ещё не началось",
	notLicensed = "Нужна лицензия преподавателя",
	notEnoughRatings = "Нужно больше оценок от учеников",
	ratingTooLow = "Рейтинг слишком низкий",
	termLimit = "Два срока подряд — предел",
	notEligible = "Нужен аккаунт от недели и полчаса игры",
	notDirector = "Только директор кампуса",
	noEventsLeft = "События на этот срок закончились",
	noCandidate = "Такого кандидата нет",
}

function CampusController.init()
	buildUi()

	Remotes.event(Remotes.Names.ClassResult).OnClientEvent:Connect(function(result: any)
		local watched = result.action == "campus"
			or result.action == "nominate"
			or result.action == "vote"
			or result.action == "subjectOfMonth"
			or result.action == "motto"
			or result.action == "startEvent"
		if not watched then
			return
		end

		if not result.ok then
			statusLabel.Text = REASONS[result.reason] or (result.reason or "Не вышло")
			return
		end
		statusLabel.Text = ""

		if result.action == "campus" then
			render(result.payload)
		else
			-- Any successful change re-reads the campus, so the panel always shows
			-- what the server actually stored rather than what was asked for.
			send("campus")
		end
	end)
end

return CampusController
