--!strict
--- Assembly task interface: labelled slots, a palette, and a submit.
---
--- Pick a slot, then pick a piece. The palette arrives shuffled and holds more
--- pieces than there are slots, so there is nothing to be inferred from its
--- order or its length.

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Remotes = require(ReplicatedStorage.Shared.Remotes)

local AssemblyController = {}

local player = Players.LocalPlayer

local PANEL = Color3.fromRGB(28, 30, 38)
local ROW = Color3.fromRGB(44, 48, 58)
local ACCENT = Color3.fromRGB(70, 96, 190)
local FILLED = Color3.fromRGB(64, 120, 150)
local TEXT = Color3.fromRGB(236, 238, 244)
local MUTED = Color3.fromRGB(150, 156, 170)

local NAMES: { [string]: string } = {
	battery = "Батарейка",
	wire = "Провод",
	lamp = "Лампа",
	switch = "Выключатель",
	resistor = "Резистор",
	magnet = "Магнит",
	thermometer = "Термометр",
	beaker = "Стакан",
	funnel = "Воронка",
	filter = "Фильтр",
	seed = "Семечко",
	soil = "Земля",
	water = "Вода",
	sunlight = "Свет",
	sprout = "Росток",
	red = "Красный",
	blue = "Синий",
	yellow = "Жёлтый",
	green = "Зелёный",
	orange = "Оранжевый",
	purple = "Фиолетовый",
	sky = "Небо",
	horizon = "Горизонт",
	foreground = "Передний план",
	shadow = "Тень",
	highlight = "Блик",
}

local panel: Frame
local promptLabel: TextLabel
local slotFrame: Frame
local paletteFrame: ScrollingFrame
local resultLabel: TextLabel

local token: string? = nil
local slotButtons: { TextButton } = {}
local assignments: { [number]: string } = {}
local selectedSlot = 1

local function corner(instance: Instance, radius: number)
	local ui = Instance.new("UICorner")
	ui.CornerRadius = UDim.new(0, radius)
	ui.Parent = instance
end

local function nameOf(id: string): string
	return NAMES[id] or id
end

local function refreshSlots(slots: { string })
	for index, button in slotButtons do
		local assigned = assignments[index]
		button.Text = if assigned ~= nil
			then `{slots[index]}: {nameOf(assigned)}`
			else `{slots[index]}: —`
		button.BackgroundColor3 = if index == selectedSlot
			then ACCENT
			elseif assigned ~= nil then FILLED
			else ROW
	end
end

local function render(payload: any)
	token = payload.token
	assignments = {}
	selectedSlot = 1
	resultLabel.Text = ""
	promptLabel.Text = payload.prompt

	for _, child in slotFrame:GetChildren() do
		if child:IsA("GuiObject") then
			child:Destroy()
		end
	end
	for _, child in paletteFrame:GetChildren() do
		if child:IsA("GuiObject") then
			child:Destroy()
		end
	end
	table.clear(slotButtons)

	for index, label in payload.slots do
		local button = Instance.new("TextButton")
		button.Size = UDim2.new(1, -8, 0, 32)
		button.Position = UDim2.fromOffset(4, (index - 1) * 36)
		button.BackgroundColor3 = ROW
		button.BorderSizePixel = 0
		button.Font = Enum.Font.GothamMedium
		button.TextSize = 14
		button.TextColor3 = TEXT
		button.TextXAlignment = Enum.TextXAlignment.Left
		button.Text = `{label}: —`
		button.Parent = slotFrame
		corner(button, 6)
		button.Activated:Connect(function()
			-- Tapping a filled slot empties it, which is the obvious way to undo.
			if assignments[index] ~= nil and selectedSlot == index then
				assignments[index] = nil
			end
			selectedSlot = index
			refreshSlots(payload.slots)
		end)
		slotButtons[index] = button
	end

	for _, piece in payload.palette do
		local button = Instance.new("TextButton")
		button.Size = UDim2.fromOffset(120, 30)
		button.BackgroundColor3 = ROW
		button.BorderSizePixel = 0
		button.Font = Enum.Font.Gotham
		button.TextSize = 13
		button.TextColor3 = TEXT
		button.Text = nameOf(piece)
		button.Parent = paletteFrame
		corner(button, 6)
		button.Activated:Connect(function()
			-- One piece per slot, and a piece already used elsewhere moves rather
			-- than duplicating: no correct task ever wants the same piece twice.
			for slot, assigned in assignments do
				if assigned == piece then
					assignments[slot] = nil
				end
			end
			assignments[selectedSlot] = piece
			if selectedSlot < #slotButtons then
				selectedSlot += 1
			end
			refreshSlots(payload.slots)
		end)
	end

	refreshSlots(payload.slots)
	panel.Visible = true
end

local function buildUi()
	local gui = Instance.new("ScreenGui")
	gui.Name = "AssemblyGui"
	gui.ResetOnSpawn = false
	gui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
	gui.Parent = player:WaitForChild("PlayerGui")

	panel = Instance.new("Frame")
	panel.Size = UDim2.fromScale(0.48, 0.62)
	panel.Position = UDim2.fromScale(0.26, 0.18)
	panel.BackgroundColor3 = PANEL
	panel.BorderSizePixel = 0
	panel.Visible = false
	panel.Parent = gui
	corner(panel, 12)

	promptLabel = Instance.new("TextLabel")
	promptLabel.Size = UDim2.new(1, -24, 0, 46)
	promptLabel.Position = UDim2.fromOffset(12, 10)
	promptLabel.BackgroundTransparency = 1
	promptLabel.Font = Enum.Font.GothamBold
	promptLabel.TextSize = 17
	promptLabel.TextColor3 = TEXT
	promptLabel.TextWrapped = true
	promptLabel.TextXAlignment = Enum.TextXAlignment.Left
	promptLabel.Text = ""
	promptLabel.Parent = panel

	slotFrame = Instance.new("Frame")
	slotFrame.Size = UDim2.new(1, -24, 0, 220)
	slotFrame.Position = UDim2.fromOffset(12, 62)
	slotFrame.BackgroundTransparency = 1
	slotFrame.Parent = panel

	local paletteCaption = Instance.new("TextLabel")
	paletteCaption.Size = UDim2.new(1, -24, 0, 18)
	paletteCaption.Position = UDim2.fromOffset(12, 288)
	paletteCaption.BackgroundTransparency = 1
	paletteCaption.Font = Enum.Font.Gotham
	paletteCaption.TextSize = 13
	paletteCaption.TextColor3 = MUTED
	paletteCaption.TextXAlignment = Enum.TextXAlignment.Left
	paletteCaption.Text = "Детали — лишние тоже есть"
	paletteCaption.Parent = panel

	paletteFrame = Instance.new("ScrollingFrame")
	paletteFrame.Size = UDim2.new(1, -24, 1, -364)
	paletteFrame.Position = UDim2.fromOffset(12, 310)
	paletteFrame.BackgroundTransparency = 1
	paletteFrame.BorderSizePixel = 0
	paletteFrame.ScrollBarThickness = 4
	paletteFrame.AutomaticCanvasSize = Enum.AutomaticSize.Y
	paletteFrame.CanvasSize = UDim2.new()
	paletteFrame.Parent = panel

	local grid = Instance.new("UIGridLayout")
	grid.CellSize = UDim2.fromOffset(120, 30)
	grid.CellPadding = UDim2.fromOffset(6, 6)
	grid.Parent = paletteFrame

	resultLabel = Instance.new("TextLabel")
	resultLabel.Size = UDim2.new(1, -170, 0, 40)
	resultLabel.Position = UDim2.new(0, 12, 1, -50)
	resultLabel.BackgroundTransparency = 1
	resultLabel.Font = Enum.Font.Gotham
	resultLabel.TextSize = 13
	resultLabel.TextColor3 = MUTED
	resultLabel.TextWrapped = true
	resultLabel.TextXAlignment = Enum.TextXAlignment.Left
	resultLabel.Text = ""
	resultLabel.Parent = panel

	local submit = Instance.new("TextButton")
	submit.Size = UDim2.fromOffset(140, 34)
	submit.Position = UDim2.new(1, -152, 1, -46)
	submit.BackgroundColor3 = ACCENT
	submit.BorderSizePixel = 0
	submit.Font = Enum.Font.GothamBold
	submit.TextSize = 15
	submit.TextColor3 = TEXT
	submit.Text = "Проверить"
	submit.Parent = panel
	corner(submit, 6)
	submit.Activated:Connect(function()
		local current = token
		if current == nil then
			return
		end
		local ordered: { any } = {}
		for index = 1, #slotButtons do
			ordered[index] = assignments[index]
		end
		Remotes.event(Remotes.Names.AssemblySubmit):FireServer({
			token = current,
			assignments = ordered,
		})
	end)
end

function AssemblyController.start(subject: string)
	Remotes.event(Remotes.Names.StartLesson):FireServer({ subject = subject, kind = "assembly" })
end

function AssemblyController.init()
	buildUi()

	Remotes.event(Remotes.Names.AssemblyTask).OnClientEvent:Connect(render)

	Remotes.event(Remotes.Names.LessonFinished).OnClientEvent:Connect(function(payload: any)
		-- Only assembly results carry an answer key; a quiz result is
		-- LessonController's to show.
		if payload.answers == nil or not panel.Visible then
			return
		end
		token = nil
		local names: { string } = {}
		for _, piece in payload.answers do
			table.insert(names, nameOf(piece))
		end
		resultLabel.Text = string.format(
			"%s · верно %d из %d · +%d баллов\nПравильно: %s\n%s",
			if payload.passed then "Задание зачтено" else "Задание не зачтено",
			payload.correctCount,
			payload.total,
			payload.pointsAwarded,
			table.concat(names, " → "),
			payload.explanation or ""
		)
		task.delay(10, function()
			if token == nil then
				panel.Visible = false
			end
		end)
	end)
end

return AssemblyController
