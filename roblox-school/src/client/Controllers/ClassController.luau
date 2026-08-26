--!strict
--- Class browser, enrolment, and the teacher's own panel.
---
--- Every action goes out on one remote with an `action` field and comes back on
--- one result remote. That keeps the metering honest -- the server rate-limits
--- per action name, and a client cannot dodge a limit by reaching for a
--- different remote.
---
--- Strings are hardcoded Russian, as in LessonController; they move into a
--- LocalizationTable with the locale work.

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Remotes = require(ReplicatedStorage.Shared.Remotes)
local CourseBuilderController = require(script.Parent.CourseBuilderController)
local LessonController = require(script.Parent.LessonController)

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
		makeLabel(row, "Пока нет классов. Создай свой или учись у ботов.", 15, MUTED, 12)
		return
	end

	for _, entry in entries do
		local row = makeRow(58)
		local promoted = if entry.promoted then "★ " else ""
		makeLabel(row, `{promoted}{entry.title}`, 16, TEXT, 6)
		local rating = if entry.ratingCount > 0
			then string.format("%.1f★ (%d)", entry.rating, entry.ratingCount)
			else "нет оценок"
		makeLabel(
			row,
			`{entry.teacherName} · {entry.subject} · {entry.grade} кл. · `
				.. `{entry.members}/{entry.capacity} · {rating}`,
			13,
			MUTED,
			30
		)

		local join = makeButton("Вступить", ACCENT, 96)
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
	local leave = makeButton("Выйти", Color3.fromRGB(120, 62, 62), 84)
	leave.Parent = header
	leave.Activated:Connect(function()
		send("leave")
		currentClassId = nil
		send("list")
	end)

	local stars = makeRow(44)
	makeLabel(stars, "Оценить класс:", 14, MUTED, 12)
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
		makeLabel(row, `{lesson.grade} класс`, 13, MUTED, 26)
		local start = makeButton("Начать", ACCENT, 90)
		start.Parent = row
		start.Activated:Connect(function()
			LessonController.startClassLesson(view.id, lesson.id)
		end)
	end
end

local function renderMine(payload: any)
	clearList()

	local head = makeRow(48)
	makeLabel(head, `Накоплено за преподавание: {math.floor(payload.pending)}`, 15, TEXT, 12)
	local collect = makeButton("Забрать", ACCENT, 90)
	collect.Parent = head
	collect.Activated:Connect(function()
		send("collect")
	end)

	for _, class in payload.classes do
		local row = makeRow(58)
		makeLabel(row, class.title, 16, TEXT, 6)
		makeLabel(
			row,
			`{class.subject} · {class.members}/{class.capacity} · уроков: {#class.lessons}`,
			13,
			MUTED,
			30
		)
		local promote = makeButton("Продвинуть", ACCENT, 110)
		promote.Parent = row
		promote.Activated:Connect(function()
			Remotes.event(Remotes.Names.RequestAd):FireServer("promoteClass")
		end)

		if class.subject == "pe" then
			local course = makeButton("Полоса", Color3.fromRGB(64, 120, 92), 90)
			course.Position = UDim2.new(1, -212, 0, 6)
			course.Parent = row
			course.Activated:Connect(function()
				CourseBuilderController.open(class.id, class.grade)
			end)
		end
	end

	if #payload.classes == 0 then
		local row = makeRow(44)
		makeLabel(row, "Класса ещё нет. Заполни поля ниже и создай.", 15, MUTED, 12)
	end
end

local function buildUi()
	local gui = Instance.new("ScreenGui")
	gui.Name = "ClassGui"
	gui.ResetOnSpawn = false
	gui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
	gui.Parent = player:WaitForChild("PlayerGui")

	local toggle = Instance.new("TextButton")
	toggle.Size = UDim2.fromOffset(120, 36)
	toggle.Position = UDim2.fromOffset(16, 16)
	toggle.BackgroundColor3 = ACCENT
	toggle.BorderSizePixel = 0
	toggle.Font = Enum.Font.GothamBold
	toggle.TextSize = 16
	toggle.TextColor3 = TEXT
	toggle.Text = "Школа"
	toggle.Parent = gui
	corner(toggle, 8)

	local panel = Instance.new("Frame")
	panel.Size = UDim2.fromScale(0.42, 0.66)
	panel.Position = UDim2.fromScale(0.03, 0.16)
	panel.BackgroundColor3 = PANEL
	panel.BorderSizePixel = 0
	panel.Visible = false
	panel.Parent = gui
	corner(panel, 12)

	toggle.Activated:Connect(function()
		panel.Visible = not panel.Visible
		if panel.Visible then
			if mode == "mine" then
				send("mine")
			elseif currentClassId ~= nil then
				send("current")
			else
				send("list")
			end
		end
	end)

	local browseTab = makeButton("Классы", ACCENT, 100)
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

	local mineTab = makeButton("Мой класс", ROW, 110)
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
	gradeBox.PlaceholderText = "класс"
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
	subjectBox.PlaceholderText = "предмет (math, logic…)"
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
	titleBox.PlaceholderText = "название класса"
	titleBox.Text = ""
	titleBox.ClearTextOnFocus = false
	titleBox.Parent = panel
	corner(titleBox, 6)

	local create = makeButton("Создать класс", ACCENT, 140)
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

local REASONS: { [string]: string } = {
	notLicensed = "Сначала нужно выпуститься и получить лицензию",
	classLimit = "Больше классов не положено без пропуска",
	titleRejected = "Название не прошло фильтр",
	unknownSubject = "Нет такого предмета",
	full = "В классе нет мест",
	ownClass = "Нельзя учиться в своём классе",
	notEnrolled = "Сначала вступи в класс",
	noClass = "Класс не найден",
	storeFailed = "Не удалось сохранить, попробуй ещё раз",
	badGrade = "Укажи класс числом от 1 до 11",
	gradeOutOfWindow = "Можно только ±1 класс от своего",
	tooShort = "Слишком короткая полоса для этого класса",
	tooLong = "Слишком длинная полоса",
	tooRepetitive = "Слишком однообразно — добавь разных модулей",
	moduleTooAdvanced = "Этот модуль недоступен на таком классе",
	wrongSubject = "Полосы только для физкультуры",
	alreadyRunning = "Ты уже проходишь полосу",
}

function ClassController.init()
	buildUi()

	Remotes.event(Remotes.Names.ClassResult).OnClientEvent:Connect(function(result: any)
		if not result.ok then
			statusLabel.Text = REASONS[result.reason] or (result.reason or "Не вышло")
			return
		end
		statusLabel.Text = ""

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
			statusLabel.Text = "Оценка учтена"
		elseif result.action == "addCourse" then
			statusLabel.Text = "Полоса сохранена"
			CourseBuilderController.close()
			send("mine")
		elseif result.action == "collect" then
			statusLabel.Text = `Забрано баллов: {result.payload or 0}`
			send("mine")
		end
	end)
end

return ClassController
