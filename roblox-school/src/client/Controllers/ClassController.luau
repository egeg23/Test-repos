--!strict
--- Class browser, enrolment, and the teacher's own panel.
---
--- Every action goes out on one remote with an `action` field and comes back on
--- one result remote. That keeps the metering honest -- the server rate-limits
--- per action name, and a client cannot dodge a limit by reaching for a
--- different remote.
---
--- All text comes from the shared Strings table, keyed by the player's locale.

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Authoring = require(ReplicatedStorage.Shared.Config.Authoring)
local Remotes = require(ReplicatedStorage.Shared.Remotes)
local L = require(script.Parent.Parent.Locale)
local HudController = require(script.Parent.HudController)
local CourseBuilderController = require(script.Parent.CourseBuilderController)
local LessonController = require(script.Parent.LessonController)
local LiveLessonController = require(script.Parent.LiveLessonController)
local QuestionEditorController = require(script.Parent.QuestionEditorController)

local ClassController = {}

local player = Players.LocalPlayer

local PANEL = Color3.fromRGB(28, 30, 38)
local ROW = Color3.fromRGB(44, 48, 58)
local ACCENT = Color3.fromRGB(70, 96, 190)
local TEXT = Color3.fromRGB(236, 238, 244)
local MUTED = Color3.fromRGB(150, 156, 170)

local listFrame: ScrollingFrame
local statusLabel: TextLabel
local titleBox: TextBox
local subjectBox: TextBox
local gradeBox: TextBox

local currentClassId: string? = nil
local mode: "browse" | "mine" = "browse"

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

local function makeButton(text: string, colour: Color3, width: number): TextButton
	local button = Instance.new("TextButton")
	button.Size = UDim2.new(0, width, 1, -12)
	button.Position = UDim2.new(1, -width - 8, 0, 6)
	button.BackgroundColor3 = colour
	button.BorderSizePixel = 0
	button.Font = Enum.Font.GothamBold
	button.TextSize = 14
	button.TextColor3 = TEXT
	button.Text = text
	corner(button, 6)
	return button
end

local function clearList()
	for _, child in listFrame:GetChildren() do
		if child:IsA("GuiObject") then
			child:Destroy()
		end
	end
end

local function makeRow(height: number): Frame
	local row = Instance.new("Frame")
	row.Size = UDim2.new(1, -8, 0, height)
	row.BackgroundColor3 = ROW
	row.BorderSizePixel = 0
	row.Parent = listFrame
	corner(row, 8)
	return row
end

local function makeLabel(parent: GuiObject, text: string, size: number, colour: Color3, y: number)
	local label = Instance.new("TextLabel")
	label.Size = UDim2.new(1, -120, 0, size + 6)
	label.Position = UDim2.new(0, 10, 0, y)
	label.BackgroundTransparency = 1
	label.Font = Enum.Font.GothamMedium
	label.TextSize = size
	label.TextColor3 = colour
	label.TextXAlignment = Enum.TextXAlignment.Left
	label.TextTruncate = Enum.TextTruncate.AtEnd
	label.Text = text
	label.Parent = parent
end

local function renderDirectory(entries: { any })
	clearList()
	if #entries == 0 then
		local row = makeRow(44)
		makeLabel(row, L.text("class.empty"), 15, MUTED, 12)
		return
	end

	for _, entry in entries do
		local row = makeRow(58)
		local promoted = if entry.promoted then "★ " else ""
		makeLabel(row, `{promoted}{entry.title}`, 16, TEXT, 6)
		local rating = if entry.ratingCount > 0
			then string.format("%.1f★ (%d)", entry.rating, entry.ratingCount)
			else L.text("class.noRatings")
		makeLabel(
			row,
			`{entry.teacherName} · {L.text(`subject.{entry.subject}`)} · `
				.. L.text("common.grade", entry.grade)
				.. ` · {entry.members}/{entry.capacity} · {rating}`,
			13,
			MUTED,
			30
		)

		local join = makeButton(L.text("class.join"), ACCENT, 96)
		join.Parent = row
		join.Activated:Connect(function()
			send("join", { classId = entry.id })
		end)
	end
end

local function renderCurrentClass(view: any)
	clearList()
	currentClassId = view.id

	local header = makeRow(58)
	makeLabel(header, view.title, 16, TEXT, 6)
	makeLabel(header, `{view.teacherName} · {view.members}/{view.capacity}`, 13, MUTED, 30)
	local leave = makeButton(L.text("common.leave"), Color3.fromRGB(120, 62, 62), 84)
	leave.Parent = header
	leave.Activated:Connect(function()
		send("leave")
		currentClassId = nil
		send("list")
	end)

	local stars = makeRow(44)
	makeLabel(stars, L.text("class.rateThis"), 14, MUTED, 12)
	for value = 1, 5 do
		local button = makeButton(tostring(value), ACCENT, 30)
		button.Position = UDim2.new(0, 130 + (value - 1) * 34, 0, 6)
		button.Parent = stars
		button.Activated:Connect(function()
			send("rate", { classId = view.id, stars = value })
		end)
	end

	for _, lesson in view.lessons do
		local row = makeRow(50)
		makeLabel(row, lesson.title, 15, TEXT, 6)
		makeLabel(row, L.text("common.grade", lesson.grade), 13, MUTED, 26)
		local start = makeButton(L.text("class.start"), ACCENT, 90)
		start.Parent = row
		start.Activated:Connect(function()
			LessonController.startClassLesson(view.id, lesson.id)
		end)
	end
end

--- A display name for a user id, from the players in this server.
---
--- The monitor may be offline, in which case there is no name to show without a
--- web call, and a number is honest where a spinner would not be.
local function nameFor(userId: number): string
	local other = Players:GetPlayerByUserId(userId)
	return if other ~= nil then other.DisplayName else `#{userId}`
end

local function renderMine(payload: any)
	clearList()

	local head = makeRow(48)
	makeLabel(head, L.text("class.earned", math.floor(payload.pending)), 15, TEXT, 12)
	local collect = makeButton(L.text("class.collect"), ACCENT, 90)
	collect.Parent = head
	collect.Activated:Connect(function()
		send("collect")
	end)

	-- When free text is switched off the editor is not disabled, it is absent:
	-- a greyed-out button still advertises a feature the build does not have,
	-- and the whole point of the switch is that nothing player-written exists.
	if Authoring.FreeTextEnabled then
		local authoring = makeRow(44)
		makeLabel(authoring, L.text("class.myQuestions"), 15, TEXT, 12)
		local openEditor = makeButton(L.text("common.open"), ACCENT, 100)
		openEditor.Parent = authoring
		openEditor.Activated:Connect(function()
			QuestionEditorController.open()
		end)
	end

	for _, class in payload.classes do
		local row = makeRow(58)
		makeLabel(row, class.title, 16, TEXT, 6)
		makeLabel(
			row,
			`{L.text(`subject.{class.subject}`)} · {class.members}/{class.capacity} · `
				.. L.text("class.lessonCount", #class.lessons),
			13,
			MUTED,
			30
		)
		local promote = makeButton(L.text("class.promote"), ACCENT, 110)
		promote.Parent = row
		promote.Activated:Connect(function()
			Remotes.event(Remotes.Names.RequestAd):FireServer("promoteClass")
		end)

		local live = makeButton(L.text("class.teachLive"), Color3.fromRGB(96, 76, 150), 118)
		live.Position = UDim2.new(1, -334, 0, 6)
		live.Parent = row
		live.Activated:Connect(function()
			local first = class.lessons[1]
			if first ~= nil then
				LiveLessonController.open(class.id, first.id)
			end
		end)

		if class.subject == "pe" then
			local course = makeButton(L.text("class.course"), Color3.fromRGB(64, 120, 92), 90)
			course.Position = UDim2.new(1, -212, 0, 6)
			course.Parent = row
			course.Activated:Connect(function()
				CourseBuilderController.open(class.id, class.grade)
			end)
		end

		-- Who the monitor is, and a way to change it. Without a control here the
		-- role would exist on the server and be unreachable from the game.
		--
		-- Candidates are the players currently in this server rather than the
		-- full roster: it needs no extra data and no name lookups, and appointing
		-- someone you are teaching right now is what a teacher would actually do.
		-- The server still checks they are enrolled.
		local monitorRow = makeRow(40)
		local monitorId = class.monitorUserId or 0
		makeLabel(
			monitorRow,
			if monitorId > 0
				then L.text("class.monitorIs", nameFor(monitorId))
				else L.text("class.noMonitor"),
			14,
			if monitorId > 0 then TEXT else MUTED,
			10
		)

		local offset = 0
		for _, other in Players:GetPlayers() do
			if other == player or offset >= 3 then
				continue
			end
			local pick = makeButton(other.DisplayName, ACCENT, 104)
			pick.Position = UDim2.new(1, -116 - offset * 110, 0, 4)
			pick.Parent = monitorRow
			pick.Activated:Connect(function()
				send("appointMonitor", { classId = class.id, userId = other.UserId })
			end)
			offset += 1
		end
		if offset == 0 then
			makeLabel(monitorRow, L.text("class.noCandidates"), 13, MUTED, 240)
		end
	end

	if #payload.classes == 0 then
		local row = makeRow(44)
		makeLabel(row, L.text("class.none"), 15, MUTED, 12)
	end
end

local function buildUi()
	local gui = Instance.new("ScreenGui")
	gui.Name = "ClassGui"
	gui.ResetOnSpawn = false
	gui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
	gui.Parent = player:WaitForChild("PlayerGui")
	local panel = Instance.new("Frame")
	panel.Size = UDim2.fromScale(0.42, 0.66)
	panel.Position = UDim2.fromScale(0.03, 0.16)
	panel.BackgroundColor3 = PANEL
	panel.BorderSizePixel = 0
	panel.Visible = false
	panel.Parent = gui
	corner(panel, 12)

	-- The toolbar owns the button and the "one panel at a time" rule; this
	-- panel only says what it is called and what to do when it opens.
	HudController.register("class", L.text("class.title"), panel, function()
		-- Which list to fetch depends on where the player left off: their own
		-- classes, the one they are enrolled in, or the directory.
		if mode == "mine" then
			send("mine")
		elseif currentClassId ~= nil then
			send("current")
		else
			send("list")
		end
	end)

	local browseTab = makeButton(L.text("class.browse"), ACCENT, 100)
	browseTab.Position = UDim2.fromOffset(12, 12)
	browseTab.Size = UDim2.fromOffset(100, 30)
	browseTab.Parent = panel
	browseTab.Activated:Connect(function()
		mode = "browse"
		if currentClassId ~= nil then
			send("current")
		else
			send("list")
		end
	end)

	local mineTab = makeButton(L.text("class.mine"), ROW, 110)
	mineTab.Position = UDim2.fromOffset(120, 12)
	mineTab.Size = UDim2.fromOffset(110, 30)
	mineTab.Parent = panel
	mineTab.Activated:Connect(function()
		mode = "mine"
		send("mine")
	end)

	listFrame = Instance.new("ScrollingFrame")
	listFrame.Size = UDim2.new(1, -24, 1, -140)
	listFrame.Position = UDim2.fromOffset(12, 52)
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

	gradeBox = Instance.new("TextBox")
	gradeBox.Size = UDim2.new(0, 56, 0, 32)
	gradeBox.Position = UDim2.new(0, 12, 1, -84)
	gradeBox.BackgroundColor3 = ROW
	gradeBox.BorderSizePixel = 0
	gradeBox.Font = Enum.Font.Gotham
	gradeBox.TextSize = 14
	gradeBox.TextColor3 = TEXT
	gradeBox.PlaceholderText = L.text("class.gradePlaceholder")
	gradeBox.Text = ""
	gradeBox.ClearTextOnFocus = false
	gradeBox.Parent = panel
	corner(gradeBox, 6)

	subjectBox = Instance.new("TextBox")
	subjectBox.Size = UDim2.new(0.4, -76, 0, 32)
	subjectBox.Position = UDim2.new(0, 74, 1, -84)
	subjectBox.BackgroundColor3 = ROW
	subjectBox.BorderSizePixel = 0
	subjectBox.Font = Enum.Font.Gotham
	subjectBox.TextSize = 14
	subjectBox.TextColor3 = TEXT
	subjectBox.PlaceholderText = L.text("class.subjectPlaceholder")
	subjectBox.Text = ""
	subjectBox.ClearTextOnFocus = false
	subjectBox.Parent = panel
	corner(subjectBox, 6)

	titleBox = Instance.new("TextBox")
	titleBox.Size = UDim2.new(0.6, -16, 0, 32)
	titleBox.Position = UDim2.new(0.4, 4, 1, -84)
	titleBox.BackgroundColor3 = ROW
	titleBox.BorderSizePixel = 0
	titleBox.Font = Enum.Font.Gotham
	titleBox.TextSize = 14
	titleBox.TextColor3 = TEXT
	titleBox.PlaceholderText = L.text("class.namePlaceholder")
	titleBox.Text = ""
	titleBox.ClearTextOnFocus = false
	titleBox.Parent = panel
	corner(titleBox, 6)

	local create = makeButton(L.text("class.create"), ACCENT, 140)
	create.Size = UDim2.fromOffset(140, 32)
	create.Position = UDim2.new(0, 12, 1, -44)
	create.Parent = panel
	create.Activated:Connect(function()
		send("create", {
			subject = subjectBox.Text,
			title = titleBox.Text,
			grade = tonumber(gradeBox.Text) or 1,
		})
	end)

	statusLabel = Instance.new("TextLabel")
	statusLabel.Size = UDim2.new(1, -170, 0, 32)
	statusLabel.Position = UDim2.new(0, 160, 1, -44)
	statusLabel.BackgroundTransparency = 1
	statusLabel.Font = Enum.Font.Gotham
	statusLabel.TextSize = 13
	statusLabel.TextColor3 = MUTED
	statusLabel.TextXAlignment = Enum.TextXAlignment.Left
	statusLabel.TextWrapped = true
	statusLabel.Text = ""
	statusLabel.Parent = panel

end

--- Shown when the server reports the last grade is finished. Until this exists
--- the flag it clears has no other way of being cleared, and every lesson is
--- refused while it is set.
local function renderGraduation()
	clearList()
	local head = makeRow(52)
	makeLabel(head, L.text("graduation.prompt"), 16, TEXT, 14)

	for _, path in { "university", "teacher", "newGamePlus" } do
		local element = makeRow(46)
		makeLabel(element, L.text(`graduation.{path}`), 15, TEXT, 12)
		local choose = makeButton(L.text("common.choose"), ACCENT, 100)
		choose.Parent = element
		choose.Activated:Connect(function()
			send("graduate", { path = path })
		end)
	end
end

function ClassController.init()
	buildUi()

	Remotes.event(Remotes.Names.ClassResult).OnClientEvent:Connect(function(result: any)
		if not result.ok then
			statusLabel.Text = if result.reason ~= nil
				then L.text(`error.{result.reason}`)
				else L.text("common.failed")
			return
		end
		statusLabel.Text = ""

		-- Nothing else is worth showing while the last grade is unresolved: the
		-- server refuses every lesson until a path is chosen.
		if result.awaitingGraduation and result.action ~= "graduate" then
			renderGraduation()
			return
		end

		if result.action == "list" then
			renderDirectory(result.payload or {})
		elseif result.action == "join" or result.action == "current" then
			if result.payload ~= nil then
				renderCurrentClass(result.payload)
			end
		elseif result.action == "mine" then
			renderMine(result.payload)
		elseif result.action == "create" then
			mode = "mine"
			send("mine")
		elseif result.action == "rate" then
			statusLabel.Text = L.text("class.rated")
		elseif result.action == "graduate" then
			statusLabel.Text = if result.payload.licensed
				then L.text("graduation.nowTeacher")
				else L.text("graduation.congratulations")
			mode = "mine"
			send("mine")
		elseif result.action == "addCourse" then
			statusLabel.Text = L.text("course.saved")
			CourseBuilderController.close()
			send("mine")
		elseif result.action == "appointMonitor" then
			statusLabel.Text = if result.ok
				then L.text("class.monitorSet")
				else L.text(`error.{result.reason or "failed"}`)
			send("mine")
		elseif result.action == "collect" then
			statusLabel.Text = L.text("class.collected", result.payload or 0)
			send("mine")
		end
	end)
end

return ClassController
