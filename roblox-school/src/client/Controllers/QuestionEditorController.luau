--!strict
--- Where a teacher writes their own questions.
---
--- The rules shown here come from the shared Authoring config, the same one the
--- server validates against, so a draft that looks acceptable is acceptable. What
--- the server does not tell this file in advance is whether the *text* will clear
--- TextService -- that answer only exists after filtering, which is why a
--- submitted question sits as pending rather than appearing immediately.

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Authoring = require(ReplicatedStorage.Shared.Config.Authoring)
local Remotes = require(ReplicatedStorage.Shared.Remotes)

local QuestionEditorController = {}

local player = Players.LocalPlayer

local PANEL = Color3.fromRGB(28, 30, 38)
local ROW = Color3.fromRGB(44, 48, 58)
local ACCENT = Color3.fromRGB(70, 96, 190)
local GOOD = Color3.fromRGB(64, 160, 92)
local WAIT = Color3.fromRGB(214, 154, 70)
local BAD = Color3.fromRGB(184, 70, 70)
local TEXT = Color3.fromRGB(236, 238, 244)
local MUTED = Color3.fromRGB(150, 156, 170)

local STATUS_NAMES: { [string]: string } = {
	pending = "на проверке",
	published = "опубликован",
	rejected = "отклонён",
}

local STATUS_COLOURS: { [string]: Color3 } = {
	pending = WAIT,
	published = GOOD,
	rejected = BAD,
}

local panel: Frame
local stemBox: TextBox
local explanationBox: TextBox
local subjectBox: TextBox
local gradeBox: TextBox
local optionBoxes: { TextBox } = {}
local answerButtons: { TextButton } = {}
local listFrame: ScrollingFrame
local statusLabel: TextLabel

local chosenAnswer = 1

local function corner(instance: Instance, radius: number)
	local ui = Instance.new("UICorner")
	ui.CornerRadius = UDim.new(0, radius)
	ui.Parent = instance
end

local function makeBox(parent: Instance, placeholder: string, size: UDim2, position: UDim2): TextBox
	local box = Instance.new("TextBox")
	box.Size = size
	box.Position = position
	box.BackgroundColor3 = ROW
	box.BorderSizePixel = 0
	box.Font = Enum.Font.Gotham
	box.TextSize = 14
	box.TextColor3 = TEXT
	box.TextXAlignment = Enum.TextXAlignment.Left
	box.TextWrapped = true
	box.PlaceholderText = placeholder
	box.Text = ""
	box.ClearTextOnFocus = false
	box.Parent = parent
	corner(box, 6)
	return box
end

local function refreshAnswerButtons()
	for index, button in answerButtons do
		button.BackgroundColor3 = if index == chosenAnswer then GOOD else PANEL
	end
end

local function renderList(questions: { any })
	for _, child in listFrame:GetChildren() do
		if child:IsA("GuiObject") then
			child:Destroy()
		end
	end

	if #questions == 0 then
		local empty = Instance.new("TextLabel")
		empty.Size = UDim2.new(1, -8, 0, 30)
		empty.BackgroundTransparency = 1
		empty.Font = Enum.Font.Gotham
		empty.TextSize = 13
		empty.TextColor3 = MUTED
		empty.TextXAlignment = Enum.TextXAlignment.Left
		empty.Text = "Своих вопросов пока нет."
		empty.Parent = listFrame
		return
	end

	for _, question in questions do
		local element = Instance.new("Frame")
		element.Size = UDim2.new(1, -8, 0, 40)
		element.BackgroundColor3 = ROW
		element.BorderSizePixel = 0
		element.Parent = listFrame
		corner(element, 6)

		local stem = Instance.new("TextLabel")
		stem.Size = UDim2.new(1, -120, 0, 18)
		stem.Position = UDim2.fromOffset(10, 4)
		stem.BackgroundTransparency = 1
		stem.Font = Enum.Font.GothamMedium
		stem.TextSize = 13
		stem.TextColor3 = TEXT
		stem.TextXAlignment = Enum.TextXAlignment.Left
		stem.TextTruncate = Enum.TextTruncate.AtEnd
		stem.Text = question.stem
		stem.Parent = element

		local status = Instance.new("TextLabel")
		status.Size = UDim2.new(0, 110, 0, 18)
		status.Position = UDim2.new(1, -116, 0, 4)
		status.BackgroundTransparency = 1
		status.Font = Enum.Font.GothamBold
		status.TextSize = 12
		status.TextColor3 = STATUS_COLOURS[question.status] or MUTED
		status.TextXAlignment = Enum.TextXAlignment.Right
		status.Text = STATUS_NAMES[question.status] or question.status
		status.Parent = element

		local meta = Instance.new("TextLabel")
		meta.Size = UDim2.new(1, -20, 0, 16)
		meta.Position = UDim2.fromOffset(10, 22)
		meta.BackgroundTransparency = 1
		meta.Font = Enum.Font.Gotham
		meta.TextSize = 12
		meta.TextColor3 = MUTED
		meta.TextXAlignment = Enum.TextXAlignment.Left
		local waiting = math.max(0, question.publishAt - os.time())
		meta.Text = if question.status == "pending"
			then `{question.subject} · {question.grade} кл. · выйдет через {math.ceil(waiting / 60)} мин`
			else `{question.subject} · {question.grade} кл. · id {question.id}`
		meta.Parent = element
	end
end

local function buildUi()
	local gui = Instance.new("ScreenGui")
	gui.Name = "QuestionEditorGui"
	gui.ResetOnSpawn = false
	gui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
	gui.Parent = player:WaitForChild("PlayerGui")

	panel = Instance.new("Frame")
	panel.Size = UDim2.fromScale(0.52, 0.72)
	panel.Position = UDim2.fromScale(0.24, 0.14)
	panel.BackgroundColor3 = PANEL
	panel.BorderSizePixel = 0
	panel.Visible = false
	panel.Parent = gui
	corner(panel, 12)

	local heading = Instance.new("TextLabel")
	heading.Size = UDim2.new(1, -24, 0, 24)
	heading.Position = UDim2.fromOffset(12, 10)
	heading.BackgroundTransparency = 1
	heading.Font = Enum.Font.GothamBold
	heading.TextSize = 17
	heading.TextColor3 = TEXT
	heading.TextXAlignment = Enum.TextXAlignment.Left
	heading.Text = "Свой вопрос"
	heading.Parent = panel

	local hint = Instance.new("TextLabel")
	hint.Size = UDim2.new(1, -24, 0, 30)
	hint.Position = UDim2.fromOffset(12, 32)
	hint.BackgroundTransparency = 1
	hint.Font = Enum.Font.Gotham
	hint.TextSize = 12
	hint.TextColor3 = MUTED
	hint.TextXAlignment = Enum.TextXAlignment.Left
	hint.TextWrapped = true
	hint.Text = string.format(
		"Вопрос до %d символов, четыре варианта примерно одной длины, объяснение "
			.. "от %d символов. Объяснение — это то, ради чего всё; оно показывается "
			.. "после ответа, верного или нет.",
		Authoring.MaxStemChars,
		Authoring.MinExplanationChars
	)
	hint.Parent = panel

	subjectBox = makeBox(panel, "предмет", UDim2.fromOffset(120, 30), UDim2.fromOffset(12, 68))
	gradeBox = makeBox(panel, "класс", UDim2.fromOffset(70, 30), UDim2.fromOffset(138, 68))
	stemBox = makeBox(
		panel,
		"текст вопроса",
		UDim2.new(1, -226, 0, 30),
		UDim2.fromOffset(214, 68)
	)

	for index = 1, Authoring.RequiredOptions do
		local y = 106 + (index - 1) * 36
		local mark = Instance.new("TextButton")
		mark.Size = UDim2.fromOffset(34, 30)
		mark.Position = UDim2.fromOffset(12, y)
		mark.BackgroundColor3 = PANEL
		mark.BorderSizePixel = 0
		mark.Font = Enum.Font.GothamBold
		mark.TextSize = 14
		mark.TextColor3 = TEXT
		mark.Text = "✓"
		mark.Parent = panel
		corner(mark, 6)
		mark.Activated:Connect(function()
			chosenAnswer = index
			refreshAnswerButtons()
		end)
		answerButtons[index] = mark

		optionBoxes[index] = makeBox(
			panel,
			`вариант {index}`,
			UDim2.new(1, -70, 0, 30),
			UDim2.fromOffset(52, y)
		)
	end
	refreshAnswerButtons()

	explanationBox = makeBox(
		panel,
		"объяснение — почему этот ответ верный",
		UDim2.new(1, -24, 0, 54),
		UDim2.fromOffset(12, 252)
	)
	explanationBox.TextYAlignment = Enum.TextYAlignment.Top

	listFrame = Instance.new("ScrollingFrame")
	listFrame.Size = UDim2.new(1, -24, 1, -394)
	listFrame.Position = UDim2.fromOffset(12, 316)
	listFrame.BackgroundTransparency = 1
	listFrame.BorderSizePixel = 0
	listFrame.ScrollBarThickness = 5
	listFrame.AutomaticCanvasSize = Enum.AutomaticSize.Y
	listFrame.CanvasSize = UDim2.new()
	listFrame.Parent = panel

	local layout = Instance.new("UIListLayout")
	layout.Padding = UDim.new(0, 5)
	layout.SortOrder = Enum.SortOrder.LayoutOrder
	layout.Parent = listFrame

	statusLabel = Instance.new("TextLabel")
	statusLabel.Size = UDim2.new(1, -300, 0, 30)
	statusLabel.Position = UDim2.new(0, 12, 1, -42)
	statusLabel.BackgroundTransparency = 1
	statusLabel.Font = Enum.Font.Gotham
	statusLabel.TextSize = 13
	statusLabel.TextColor3 = MUTED
	statusLabel.TextXAlignment = Enum.TextXAlignment.Left
	statusLabel.TextWrapped = true
	statusLabel.Text = ""
	statusLabel.Parent = panel

	local submit = Instance.new("TextButton")
	submit.Size = UDim2.fromOffset(140, 30)
	submit.Position = UDim2.new(1, -152, 1, -42)
	submit.BackgroundColor3 = ACCENT
	submit.BorderSizePixel = 0
	submit.Font = Enum.Font.GothamBold
	submit.TextSize = 14
	submit.TextColor3 = TEXT
	submit.Text = "Отправить"
	submit.Parent = panel
	corner(submit, 6)
	submit.Activated:Connect(function()
		local options: { string } = {}
		for _, box in optionBoxes do
			table.insert(options, box.Text)
		end
		Remotes.event(Remotes.Names.ClassAction):FireServer({
			action = "submitQuestion",
			draft = {
				subject = subjectBox.Text,
				grade = tonumber(gradeBox.Text) or 1,
				stem = stemBox.Text,
				options = options,
				answer = chosenAnswer,
				explanation = explanationBox.Text,
			},
		})
	end)

	local close = Instance.new("TextButton")
	close.Size = UDim2.fromOffset(28, 28)
	close.Position = UDim2.new(1, -38, 0, 10)
	close.BackgroundColor3 = ROW
	close.BorderSizePixel = 0
	close.Font = Enum.Font.GothamBold
	close.TextSize = 16
	close.TextColor3 = TEXT
	close.Text = "×"
	close.Parent = panel
	corner(close, 6)
	close.Activated:Connect(function()
		panel.Visible = false
	end)
end

local REASONS: { [string]: string } = {
	stemTooShort = "Вопрос слишком короткий",
	stemTooLong = "Вопрос слишком длинный",
	optionCount = "Нужно ровно четыре варианта",
	badAnswer = "Отметь верный вариант",
	emptyOption = "Один из вариантов пустой",
	optionTooLong = "Вариант слишком длинный",
	duplicateOption = "Два варианта совпадают",
	lopsidedOptions = "Один вариант заметно длиннее — по нему угадают",
	explanationTooShort = "Объяснение слишком короткое",
	explanationTooLong = "Объяснение слишком длинное",
	badGrade = "Класс от 1 до 11",
	textRejected = "Текст не прошёл фильтр",
	authoredLimit = "Слишком много своих вопросов",
	unknownSubject = "Нет такого предмета",
	notLicensed = "Нужна лицензия преподавателя",
}

function QuestionEditorController.open()
	panel.Visible = true
	Remotes.event(Remotes.Names.ClassAction):FireServer({ action = "myQuestions" })
end

function QuestionEditorController.init()
	buildUi()

	Remotes.event(Remotes.Names.ClassResult).OnClientEvent:Connect(function(result: any)
		if result.action == "myQuestions" then
			if result.ok then
				renderList(result.payload or {})
			end
			return
		end
		if result.action ~= "submitQuestion" then
			return
		end

		if not result.ok then
			statusLabel.Text = REASONS[result.reason] or (result.reason or "Не вышло")
			return
		end
		statusLabel.Text = "Отправлено. Появится после проверки."
		stemBox.Text = ""
		explanationBox.Text = ""
		for _, box in optionBoxes do
			box.Text = ""
		end
		Remotes.event(Remotes.Names.ClassAction):FireServer({ action = "myQuestions" })
	end)
end

return QuestionEditorController
