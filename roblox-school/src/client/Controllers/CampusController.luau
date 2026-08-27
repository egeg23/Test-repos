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
local L = require(script.Parent.Parent.Locale)
local HudController = require(script.Parent.HudController)

local CampusController = {}

local player = Players.LocalPlayer

local PANEL = Color3.fromRGB(28, 30, 38)
local ROW = Color3.fromRGB(44, 48, 58)
local ACCENT = Color3.fromRGB(70, 96, 190)
local TEXT = Color3.fromRGB(236, 238, 244)
local MUTED = Color3.fromRGB(150, 156, 170)

local reviewSubject: string? = nil
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
	local week = L.text("campus.calendar", view.termIndex + 1, view.weekInTerm + 1, view.weeksPerTerm)
	local calendar = if view.isTestWeek then L.text("campus.testWeek", week) else week
	phaseLabel.Text = `{L.text(`campus.{view.phase}`)} · {calendar}`

	local head = row(72)
	text(
		head,
		if view.directorUserId > 0
			then L.text("campus.director", view.directorName)
			else L.text("campus.noDirector"),
		16,
		TEXT,
		8
	)
	local extras = {}
	if view.subjectOfMonth ~= nil then
		table.insert(extras, L.text("campus.subjectOfMonth", L.text(`subject.{view.subjectOfMonth}`)))
	end
	if view.motto ~= nil then
		table.insert(extras, L.text(view.motto))
	end
	if view.eventUntil > os.time() then
		table.insert(extras, L.text("campus.eventRunning"))
	end
	text(
		head,
		if #extras > 0 then table.concat(extras, " · ") else L.text("campus.daysLeft", remaining),
		13,
		MUTED,
		34
	)

	if view.phase == "campaign" then
		local stand = row(46)
		text(stand, L.text("campus.stand"), 15, TEXT, 12)
		action(stand, L.text("campus.standButton"), ACCENT, 120).Activated:Connect(function()
			send("nominate")
		end)
	end

	for _, candidate in view.candidates do
		local element = row(46)
		text(element, L.text("campus.votes", candidate.name, math.floor(candidate.votes)), 15, TEXT, 12)
		if view.phase == "voting" then
			action(element, L.text("campus.vote"), ACCENT, 90).Activated:Connect(function()
				send("vote", { candidateUserId = candidate.userId })
			end)
		end
	end

	if view.phase ~= "term" and #view.candidates == 0 then
		text(row(40), L.text("campus.noCandidates"), 15, MUTED, 10)
	end

	-- The director's own controls. Shown when the server says this player holds
	-- the office; refused server-side regardless.
	if view.directorUserId == player.UserId then
		local eventRow = row(46)
		text(eventRow, L.text("campus.event", view.eventsLeft), 15, TEXT, 12)
		action(eventRow, L.text("campus.launch"), ACCENT, 110).Activated:Connect(function()
			send("startEvent")
		end)

		local subjectRow = row(76)
		text(subjectRow, L.text("campus.pickSubject"), 15, TEXT, 6)
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
			button.Text = L.text(entry.displayKey)
			button.Parent = subjectRow
			corner(button, 5)
			button.Activated:Connect(function()
				send("subjectOfMonth", { subject = entry.id })
			end)
			index += 1
		end

		local mottoRow = row(76)
		text(mottoRow, L.text("campus.motto"), 15, TEXT, 6)
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
			button.Text = L.text(key)
			button.Parent = mottoRow
			corner(button, 5)
			button.Activated:Connect(function()
				send("motto", { motto = key })
			end)
			mottoIndex += 1
		end
	end

	-- A dean's own queue. Shown here rather than in a panel of its own because
	-- the office is a campus office, and this is where a player comes to see what
	-- their office lets them do.
	if #view.deanOf > 0 then
		local subjects: { string } = {}
		for _, subject in view.deanOf do
			table.insert(subjects, L.text(`subject.{subject}`))
		end

		local deanRow = row(46)
		text(deanRow, L.text("review.deanOf", table.concat(subjects, ", ")), 15, TEXT, 12)
		action(deanRow, L.text("common.open"), ACCENT, 100).Activated:Connect(function()
			reviewSubject = view.deanOf[1]
			send("reviewQueue", { subject = reviewSubject })
		end)
	end

	local deanNames: { string } = {}
	for subject, name in view.deans do
		table.insert(deanNames, `{subject}: {name}`)
	end
	if #deanNames > 0 then
		text(row(40), L.text("campus.deans", table.concat(deanNames, ", ")), 13, MUTED, 12)
	end
end

--- The pending questions in a subject this player is dean of. Answer and
--- explanation are shown: a dean judging a question without seeing what it
--- claims is right is not reviewing anything.
local function renderQueue(entries: { any })
	clearList()

	local head = row(46)
	text(head, L.text("review.queue", #entries), 16, TEXT, 12)
	action(head, L.text("campus.title"), ROW, 100).Activated:Connect(function()
		reviewSubject = nil
		send("campus")
	end)

	if #entries == 0 then
		text(row(40), L.text("review.none"), 15, MUTED, 10)
		return
	end

	for _, item in entries do
		local element = row(96)
		text(element, item.stem, 15, TEXT, 8)
		text(
			element,
			L.text("review.answer", item.options[item.answer] or "?"),
			13,
			MUTED,
			30
		)
		text(element, item.explanation, 12, MUTED, 50)

		local approve = action(element, L.text("review.approve"), ACCENT, 108)
		approve.Position = UDim2.new(1, -116, 0, 8)
		approve.Activated:Connect(function()
			send("reviewQuestion", {
				subject = reviewSubject,
				teacherUserId = item.teacherUserId,
				questionId = item.questionId,
				approve = true,
			})
		end)

		local reject = action(element, L.text("review.reject"), Color3.fromRGB(120, 62, 62), 108)
		reject.Position = UDim2.new(1, -116, 0, 48)
		reject.Activated:Connect(function()
			send("reviewQuestion", {
				subject = reviewSubject,
				teacherUserId = item.teacherUserId,
				questionId = item.questionId,
				approve = false,
			})
		end)
	end
end

local function buildUi()
	local gui = Instance.new("ScreenGui")
	gui.Name = "CampusGui"
	gui.ResetOnSpawn = false
	gui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
	gui.Parent = player:WaitForChild("PlayerGui")

	panel = Instance.new("Frame")
	panel.Size = UDim2.fromScale(0.44, 0.62)
	panel.Position = UDim2.fromScale(0.28, 0.18)
	panel.BackgroundColor3 = PANEL
	panel.BorderSizePixel = 0
	panel.Visible = false
	panel.Parent = gui
	corner(panel, 12)

	-- The toolbar owns the button and the "one panel at a time" rule; this
	-- panel only says what it is called and what to do when it opens.
	HudController.register("campus", L.text("campus.title"), panel, function()
		send("campus")
	end)

	headerLabel = Instance.new("TextLabel")
	headerLabel.Size = UDim2.new(1, -24, 0, 24)
	headerLabel.Position = UDim2.fromOffset(12, 10)
	headerLabel.BackgroundTransparency = 1
	headerLabel.Font = Enum.Font.GothamBold
	headerLabel.TextSize = 17
	headerLabel.TextColor3 = TEXT
	headerLabel.TextXAlignment = Enum.TextXAlignment.Left
	headerLabel.Text = L.text("campus.title")
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

function CampusController.init()
	buildUi()

	Remotes.event(Remotes.Names.ClassResult).OnClientEvent:Connect(function(result: any)
		local watched = result.action == "campus"
			or result.action == "reviewQueue"
			or result.action == "reviewQuestion"
			or result.action == "nominate"
			or result.action == "vote"
			or result.action == "subjectOfMonth"
			or result.action == "motto"
			or result.action == "startEvent"
		if not watched then
			return
		end

		if not result.ok then
			statusLabel.Text = if result.reason ~= nil
				then L.text(`error.{result.reason}`)
				else L.text("common.failed")
			return
		end
		statusLabel.Text = ""

		if result.action == "campus" then
			render(result.payload)
		elseif result.action == "reviewQueue" then
			renderQueue(result.payload or {})
		elseif result.action == "reviewQuestion" then
			statusLabel.Text = L.text("review.done")
			send("reviewQueue", { subject = reviewSubject })
		else
			-- Any successful change re-reads the campus, so the panel always shows
			-- what the server actually stored rather than what was asked for.
			send("campus")
		end
	end)
end

return CampusController
