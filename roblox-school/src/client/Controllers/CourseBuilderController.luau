--!strict
--- The teacher's obstacle course builder.
---
--- Reads the same Obstacles config the server validates against, so the rules are
--- visible while building rather than reported as a rejection afterwards: the
--- grade window is drawn as the only buttons that exist, and the module count is
--- shown against the number the chosen grade demands. The server still checks
--- everything -- this is the courtesy, not the enforcement.

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Obstacles = require(ReplicatedStorage.Shared.Config.Obstacles)
local Remotes = require(ReplicatedStorage.Shared.Remotes)

local CourseBuilderController = {}

local player = Players.LocalPlayer

local PANEL = Color3.fromRGB(28, 30, 38)
local ROW = Color3.fromRGB(44, 48, 58)
local ACCENT = Color3.fromRGB(70, 96, 190)
local GOOD = Color3.fromRGB(64, 160, 92)
local TEXT = Color3.fromRGB(236, 238, 244)
local MUTED = Color3.fromRGB(150, 156, 170)

local MODULE_NAMES: { [string]: string } = {
	gap = "Пропасть",
	narrowBeam = "Узкая балка",
	movingPlatform = "Движущаяся платформа",
	vanishingTiles = "Исчезающие плитки",
	spinner = "Вертушка",
	hazardField = "Поле шипов",
}

local panel: Frame
local gradeRow: Frame
local moduleRow: ScrollingFrame
local sequenceLabel: TextLabel
local requirementLabel: TextLabel
local titleBox: TextBox

local classId: string? = nil
local classGrade = 1
local chosenGrade = 1
local sequence: { string } = {}

local function corner(instance: Instance, radius: number)
	local ui = Instance.new("UICorner")
	ui.CornerRadius = UDim.new(0, radius)
	ui.Parent = instance
end

local function button(parent: Instance, text: string, colour: Color3, size: UDim2): TextButton
	local element = Instance.new("TextButton")
	element.Size = size
	element.BackgroundColor3 = colour
	element.BorderSizePixel = 0
	element.Font = Enum.Font.GothamMedium
	element.TextSize = 14
	element.TextColor3 = TEXT
	element.TextWrapped = true
	element.Text = text
	element.Parent = parent
	corner(element, 6)
	return element
end

local refresh: () -> ()

local function renderModules()
	for _, child in moduleRow:GetChildren() do
		if child:IsA("GuiObject") then
			child:Destroy()
		end
	end
	for _, entry in Obstacles.modulesForGrade(chosenGrade) do
		local element = button(
			moduleRow,
			MODULE_NAMES[entry.id] or entry.id,
			ROW,
			UDim2.new(0, 150, 0, 34)
		)
		element.Activated:Connect(function()
			table.insert(sequence, entry.id)
			refresh()
		end)
	end
end

local function renderGrades()
	for _, child in gradeRow:GetChildren() do
		if child:IsA("GuiObject") then
			child:Destroy()
		end
	end
	local low, high = Obstacles.allowedGrades(classGrade)
	local index = 0
	for grade = low, high do
		local element = button(
			gradeRow,
			tostring(grade),
			if grade == chosenGrade then ACCENT else ROW,
			UDim2.new(0, 44, 1, 0)
		)
		element.Position = UDim2.new(0, index * 50, 0, 0)
		element.Activated:Connect(function()
			chosenGrade = grade
			-- A harder grade can unlock modules the current sequence used and an
			-- easier one can forbid them, so the sequence starts over.
			sequence = {}
			refresh()
		end)
		index += 1
	end
end

refresh = function()
	renderGrades()
	renderModules()

	local params = Obstacles.paramsForGrade(chosenGrade)
	local required = Obstacles.requiredDistinctTypes(chosenGrade, #sequence)
	local distinct: { [string]: boolean } = {}
	local distinctCount = 0
	local names: { string } = {}
	for _, id in sequence do
		table.insert(names, MODULE_NAMES[id] or id)
		if not distinct[id] then
			distinct[id] = true
			distinctCount += 1
		end
	end

	sequenceLabel.Text = if #sequence == 0
		then "Пока пусто. Нажимай модули выше."
		else table.concat(names, " → ")

	requirementLabel.Text = string.format(
		"Модулей: %d из %d · Разных типов: %d из %d · Пропасть %.0f · Балка %.1f · %s",
		#sequence,
		params.moduleCount,
		distinctCount,
		required,
		params.gapStuds,
		params.beamWidth,
		if params.checkpointEvery == 0
			then "без чекпоинтов"
			else `чекпоинт каждые {params.checkpointEvery}`
	)
	requirementLabel.TextColor3 = if #sequence >= params.moduleCount
			and distinctCount >= required
		then GOOD
		else MUTED
end

local function buildUi()
	local gui = Instance.new("ScreenGui")
	gui.Name = "CourseBuilderGui"
	gui.ResetOnSpawn = false
	gui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
	gui.Parent = player:WaitForChild("PlayerGui")

	panel = Instance.new("Frame")
	panel.Size = UDim2.fromScale(0.5, 0.5)
	panel.Position = UDim2.fromScale(0.25, 0.25)
	panel.BackgroundColor3 = PANEL
	panel.BorderSizePixel = 0
	panel.Visible = false
	panel.Parent = gui
	corner(panel, 12)

	local heading = Instance.new("TextLabel")
	heading.Size = UDim2.new(1, -24, 0, 26)
	heading.Position = UDim2.fromOffset(12, 10)
	heading.BackgroundTransparency = 1
	heading.Font = Enum.Font.GothamBold
	heading.TextSize = 17
	heading.TextColor3 = TEXT
	heading.TextXAlignment = Enum.TextXAlignment.Left
	heading.Text = "Полоса препятствий"
	heading.Parent = panel

	local gradeCaption = Instance.new("TextLabel")
	gradeCaption.Size = UDim2.new(0, 120, 0, 20)
	gradeCaption.Position = UDim2.fromOffset(12, 42)
	gradeCaption.BackgroundTransparency = 1
	gradeCaption.Font = Enum.Font.Gotham
	gradeCaption.TextSize = 13
	gradeCaption.TextColor3 = MUTED
	gradeCaption.TextXAlignment = Enum.TextXAlignment.Left
	gradeCaption.Text = "Сложность (класс):"
	gradeCaption.Parent = panel

	gradeRow = Instance.new("Frame")
	gradeRow.Size = UDim2.new(1, -150, 0, 30)
	gradeRow.Position = UDim2.fromOffset(140, 38)
	gradeRow.BackgroundTransparency = 1
	gradeRow.Parent = panel

	moduleRow = Instance.new("ScrollingFrame")
	moduleRow.Size = UDim2.new(1, -24, 0, 80)
	moduleRow.Position = UDim2.fromOffset(12, 78)
	moduleRow.BackgroundTransparency = 1
	moduleRow.BorderSizePixel = 0
	moduleRow.ScrollBarThickness = 4
	moduleRow.AutomaticCanvasSize = Enum.AutomaticSize.Y
	moduleRow.CanvasSize = UDim2.new()
	moduleRow.Parent = panel

	local grid = Instance.new("UIGridLayout")
	grid.CellSize = UDim2.fromOffset(150, 34)
	grid.CellPadding = UDim2.fromOffset(6, 6)
	grid.Parent = moduleRow

	sequenceLabel = Instance.new("TextLabel")
	sequenceLabel.Size = UDim2.new(1, -24, 0, 54)
	sequenceLabel.Position = UDim2.fromOffset(12, 166)
	sequenceLabel.BackgroundColor3 = ROW
	sequenceLabel.BorderSizePixel = 0
	sequenceLabel.Font = Enum.Font.Gotham
	sequenceLabel.TextSize = 13
	sequenceLabel.TextColor3 = TEXT
	sequenceLabel.TextWrapped = true
	sequenceLabel.Text = ""
	sequenceLabel.Parent = panel
	corner(sequenceLabel, 6)

	requirementLabel = Instance.new("TextLabel")
	requirementLabel.Size = UDim2.new(1, -24, 0, 34)
	requirementLabel.Position = UDim2.fromOffset(12, 226)
	requirementLabel.BackgroundTransparency = 1
	requirementLabel.Font = Enum.Font.GothamMedium
	requirementLabel.TextSize = 13
	requirementLabel.TextColor3 = MUTED
	requirementLabel.TextWrapped = true
	requirementLabel.TextXAlignment = Enum.TextXAlignment.Left
	requirementLabel.Text = ""
	requirementLabel.Parent = panel

	titleBox = Instance.new("TextBox")
	titleBox.Size = UDim2.new(0.5, -18, 0, 32)
	titleBox.Position = UDim2.new(0, 12, 1, -46)
	titleBox.BackgroundColor3 = ROW
	titleBox.BorderSizePixel = 0
	titleBox.Font = Enum.Font.Gotham
	titleBox.TextSize = 14
	titleBox.TextColor3 = TEXT
	titleBox.PlaceholderText = "название полосы"
	titleBox.Text = ""
	titleBox.ClearTextOnFocus = false
	titleBox.Parent = panel
	corner(titleBox, 6)

	local undo = button(panel, "Убрать последний", ROW, UDim2.fromOffset(150, 32))
	undo.Position = UDim2.new(0.5, 0, 1, -46)
	undo.Activated:Connect(function()
		if #sequence > 0 then
			table.remove(sequence)
			refresh()
		end
	end)

	local save = button(panel, "Сохранить", ACCENT, UDim2.fromOffset(120, 32))
	save.Position = UDim2.new(1, -132, 1, -46)
	save.Activated:Connect(function()
		local target = classId
		if target == nil then
			return
		end
		Remotes.event(Remotes.Names.ClassAction):FireServer({
			action = "addCourse",
			classId = target,
			title = titleBox.Text,
			grade = chosenGrade,
			moduleIds = sequence,
		})
	end)

	local close = button(panel, "×", ROW, UDim2.fromOffset(28, 28))
	close.Position = UDim2.new(1, -38, 0, 10)
	close.Activated:Connect(function()
		panel.Visible = false
	end)
end

function CourseBuilderController.open(targetClassId: string, grade: number)
	classId = targetClassId
	classGrade = grade
	chosenGrade = grade
	sequence = {}
	panel.Visible = true
	refresh()
end

function CourseBuilderController.close()
	panel.Visible = false
end

function CourseBuilderController.init()
	buildUi()
end

return CourseBuilderController
