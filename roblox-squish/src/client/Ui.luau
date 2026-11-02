--!strict
--- Small helpers for building the interface in the game's pastel style.
---
--- Every panel is made of the same few pieces -- a rounded panel, a soft
--- button, a label -- so they all look like one game, and a colour change is
--- one edit in Config/Palette.

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Palette = require(ReplicatedStorage.Shared.Config.Palette)

local Ui = {}

Ui.Font = Enum.Font.FredokaOne
Ui.BodyFont = Enum.Font.Gotham

function Ui.colour(name: string): Color3
	return Palette.colour((Palette.Ui :: any)[name])
end

function Ui.screen(name: string, order: number?): ScreenGui
	local gui = Instance.new("ScreenGui")
	gui.Name = name
	gui.ResetOnSpawn = false
	gui.IgnoreGuiInset = false
	gui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
	gui.DisplayOrder = order or 0
	gui.Parent = Players.LocalPlayer:WaitForChild("PlayerGui")
	return gui
end

function Ui.corner(instance: GuiObject, radius: number?)
	local c = Instance.new("UICorner")
	c.CornerRadius = UDim.new(0, radius or 14)
	c.Parent = instance
end

function Ui.stroke(instance: GuiObject, colour: Color3, thickness: number?)
	local s = Instance.new("UIStroke")
	s.Color = colour
	s.Thickness = thickness or 2
	s.ApplyStrokeMode = Enum.ApplyStrokeMode.Border
	s.Parent = instance
	return s
end

function Ui.padding(instance: GuiObject, px: number)
	local p = Instance.new("UIPadding")
	p.PaddingTop = UDim.new(0, px)
	p.PaddingBottom = UDim.new(0, px)
	p.PaddingLeft = UDim.new(0, px)
	p.PaddingRight = UDim.new(0, px)
	p.Parent = instance
end

function Ui.list(instance: GuiObject, gap: number, horizontal: boolean?)
	local layout = Instance.new("UIListLayout")
	layout.Padding = UDim.new(0, gap)
	layout.FillDirection = if horizontal then Enum.FillDirection.Horizontal else Enum.FillDirection.Vertical
	layout.SortOrder = Enum.SortOrder.LayoutOrder
	layout.HorizontalAlignment = Enum.HorizontalAlignment.Center
	layout.Parent = instance
	return layout
end

--- A centred panel with a title row and a close button. Returns the panel and
--- its scrolling body.
function Ui.panel(parent: Instance, title: string, width: number, height: number): (Frame, ScrollingFrame, TextLabel)
	local frame = Instance.new("Frame")
	frame.Name = "Panel"
	frame.AnchorPoint = Vector2.new(0.5, 0.5)
	frame.Position = UDim2.fromScale(0.5, 0.5)
	frame.Size = UDim2.new(0, width, 0, height)
	frame.BackgroundColor3 = Ui.colour("panel")
	frame.Visible = false
	frame.Parent = parent
	Ui.corner(frame, 22)
	Ui.stroke(frame, Ui.colour("panelEdge"), 4)
	local constraint = Instance.new("UISizeConstraint")
	constraint.MaxSize = Vector2.new(width, height)
	constraint.Parent = frame
	-- Fits small phone screens: never wider or taller than 94% of the view.
	frame.Size = UDim2.new(0.94, 0, 0.86, 0)

	local heading = Ui.label(frame, title, 26, "ink")
	heading.Name = "Title"
	heading.Size = UDim2.new(1, -70, 0, 44)
	heading.Position = UDim2.new(0, 18, 0, 8)
	heading.TextXAlignment = Enum.TextXAlignment.Left

	local close = Ui.button(frame, "×", "button")
	close.Name = "Close"
	close.Size = UDim2.new(0, 40, 0, 40)
	close.Position = UDim2.new(1, -50, 0, 10)
	close.Activated:Connect(function()
		frame.Visible = false
	end)

	local body = Instance.new("ScrollingFrame")
	body.Name = "Body"
	body.BackgroundTransparency = 1
	body.BorderSizePixel = 0
	body.Position = UDim2.new(0, 12, 0, 60)
	body.Size = UDim2.new(1, -24, 1, -72)
	body.AutomaticCanvasSize = Enum.AutomaticSize.Y
	body.CanvasSize = UDim2.new()
	body.ScrollBarThickness = 6
	body.ScrollBarImageColor3 = Ui.colour("panelEdge")
	body.Parent = frame
	Ui.list(body, 8)
	return frame, body, heading
end

function Ui.label(parent: Instance, text: string, size: number, colourName: string?): TextLabel
	local label = Instance.new("TextLabel")
	label.BackgroundTransparency = 1
	label.Font = Ui.Font
	label.TextSize = size
	label.TextColor3 = Ui.colour(colourName or "ink")
	label.TextWrapped = true
	label.Text = text
	label.Size = UDim2.new(1, 0, 0, size + 10)
	label.Parent = parent
	return label
end

function Ui.button(parent: Instance, text: string, colourName: string?): TextButton
	local button = Instance.new("TextButton")
	button.AutoButtonColor = true
	button.BackgroundColor3 = Ui.colour(colourName or "button")
	button.Font = Ui.Font
	button.TextSize = 20
	button.TextColor3 = Ui.colour("buttonInk")
	button.TextWrapped = true
	button.Text = text
	button.Size = UDim2.new(0, 160, 0, 44)
	button.Parent = parent
	Ui.corner(button, 14)
	return button
end

function Ui.clear(container: Instance)
	for _, child in container:GetChildren() do
		if child:IsA("GuiObject") then
			child:Destroy()
		end
	end
end

--- 1234 -> 1.2K, so big numbers fit on a phone. Suffixes are symbols, not
--- words, and read the same in all four languages.
function Ui.short(value: number): string
	local abs = math.abs(value)
	local units = { { 1e12, "T" }, { 1e9, "B" }, { 1e6, "M" }, { 1e3, "K" } }
	for _, unit in units do
		if abs >= unit[1] :: number then
			return string.format("%.1f%s", value / (unit[1] :: number), unit[2] :: string)
		end
	end
	return tostring(math.floor(value))
end

function Ui.clock(seconds: number): string
	seconds = math.max(0, math.floor(seconds))
	if seconds >= 3600 then
		return string.format("%d:%02d:%02d", seconds // 3600, (seconds % 3600) // 60, seconds % 60)
	end
	return string.format("%d:%02d", seconds // 60, seconds % 60)
end

--- A long countdown, such as days to the end of the show week.
function Ui.duration(seconds: number): string
	seconds = math.max(0, math.floor(seconds))
	if seconds >= 86400 then
		return string.format("%dd %dh", seconds // 86400, (seconds % 86400) // 3600)
	end
	return Ui.clock(seconds)
end

function Ui.rarityColour(rarity: string): Color3
	local Squishes = require(ReplicatedStorage.Shared.Config.Squishes)
	local info = (Squishes.Rarities :: any)[rarity]
	if info == nil then
		return Ui.colour("muted")
	end
	return Palette.colour(info.colour)
end

return Ui
