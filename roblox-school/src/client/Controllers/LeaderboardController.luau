--!strict
--- The weekly boards.
---
--- Three tabs, ten rows, and the player's own row always shown -- on the board
--- if they made it, underneath if they did not. A board that shows a player
--- nothing about themselves is a board they look at once.

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Remotes = require(ReplicatedStorage.Shared.Remotes)
local L = require(script.Parent.Parent.Locale)
local HudController = require(script.Parent.HudController)

local LeaderboardController = {}

local player = Players.LocalPlayer

local PANEL = Color3.fromRGB(28, 30, 38)
local ROW = Color3.fromRGB(44, 48, 58)
local ACCENT = Color3.fromRGB(70, 96, 190)
local GOLD = Color3.fromRGB(206, 166, 78)
local TEXT = Color3.fromRGB(236, 238, 244)
local MUTED = Color3.fromRGB(150, 156, 170)

--- Mirrors LeaderboardService.Boards. Listed rather than sent because the tabs
--- have to exist before the first reply arrives, and a panel that draws its own
--- tabs only after a round trip opens empty every time.
local BOARDS = { "lessons", "courses", "teaching" }

local panel: Frame
local tabRow: Frame
local listFrame: ScrollingFrame
local yoursLabel: TextLabel
local current = BOARDS[1]

local function corner(instance: Instance, radius: number)
	local ui = Instance.new("UICorner")
	ui.CornerRadius = UDim.new(0, radius)
	ui.Parent = instance
end

local function send(boardId: string)
	Remotes.event(Remotes.Names.ClassAction):FireServer({ action = "board", boardId = boardId })
end

local function renderTabs()
	for _, child in tabRow:GetChildren() do
		if child:IsA("GuiObject") then
			child:Destroy()
		end
	end
	for index, id in BOARDS do
		local tab = Instance.new("TextButton")
		tab.Size = UDim2.fromOffset(112, 28)
		tab.Position = UDim2.fromOffset((index - 1) * 118, 0)
		tab.BackgroundColor3 = if id == current then ACCENT else ROW
		tab.BorderSizePixel = 0
		tab.Font = Enum.Font.GothamMedium
		tab.TextSize = 13
		tab.TextColor3 = TEXT
		tab.Text = L.text(`board.{id}`)
		tab.Parent = tabRow
		corner(tab, 6)
		tab.Activated:Connect(function()
			current = id
			renderTabs()
			send(id)
		end)
	end
end

local function render(payload: any)
	for _, child in listFrame:GetChildren() do
		if child:IsA("Frame") then
			child:Destroy()
		end
	end
	if payload == nil then
		return
	end

	yoursLabel.Text = L.text("board.you", payload.yours or 0)

	if #payload.rows == 0 then
		local empty = Instance.new("Frame")
		empty.Size = UDim2.new(1, 0, 0, 34)
		empty.BackgroundTransparency = 1
		empty.Parent = listFrame

		local text = Instance.new("TextLabel")
		text.Size = UDim2.fromScale(1, 1)
		text.BackgroundTransparency = 1
		text.Font = Enum.Font.Gotham
		text.TextSize = 14
		text.TextColor3 = MUTED
		text.TextXAlignment = Enum.TextXAlignment.Left
		text.Text = L.text("board.empty")
		text.Parent = empty
		return
	end

	for _, entry in payload.rows do
		local row = Instance.new("Frame")
		row.Size = UDim2.new(1, 0, 0, 30)
		row.BackgroundColor3 = if entry.isYou then ACCENT else ROW
		row.BorderSizePixel = 0
		row.LayoutOrder = entry.rank
		row.Parent = listFrame
		corner(row, 6)

		local function cell(text: string, x: number, width: number, colour: Color3, align: Enum.TextXAlignment)
			local item = Instance.new("TextLabel")
			item.Size = UDim2.new(0, width, 1, 0)
			item.Position = UDim2.fromOffset(x, 0)
			item.BackgroundTransparency = 1
			item.Font = Enum.Font.GothamMedium
			item.TextSize = 14
			item.TextColor3 = colour
			item.TextXAlignment = align
			item.TextTruncate = Enum.TextTruncate.AtEnd
			item.Text = text
			item.Parent = row
		end

		cell(tostring(entry.rank), 10, 28, if entry.rank <= 3 then GOLD else MUTED, Enum.TextXAlignment.Left)
		-- The name comes from another player's DisplayName, relayed by the
		-- server. It is set as Text on a TextLabel, which does not interpret
		-- markup, so there is nothing here for a crafted name to do.
		cell(tostring(entry.name), 44, 190, TEXT, Enum.TextXAlignment.Left)
		cell(tostring(entry.score), 240, 60, TEXT, Enum.TextXAlignment.Right)
	end
end

local function buildUi()
	local gui = Instance.new("ScreenGui")
	gui.Name = "LeaderboardGui"
	gui.ResetOnSpawn = false
	gui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
	gui.Parent = player:WaitForChild("PlayerGui")

	panel = Instance.new("Frame")
	panel.Size = UDim2.fromScale(0.32, 0.6)
	panel.Position = UDim2.fromScale(0.34, 0.18)
	panel.BackgroundColor3 = PANEL
	panel.BorderSizePixel = 0
	panel.Visible = false
	panel.Parent = gui
	corner(panel, 12)

	HudController.register("board", L.text("board.title"), panel, function()
		send(current)
	end)

	tabRow = Instance.new("Frame")
	tabRow.Size = UDim2.new(1, -24, 0, 28)
	tabRow.Position = UDim2.fromOffset(12, 12)
	tabRow.BackgroundTransparency = 1
	tabRow.Parent = panel

	yoursLabel = Instance.new("TextLabel")
	yoursLabel.Size = UDim2.new(1, -24, 0, 20)
	yoursLabel.Position = UDim2.fromOffset(12, 46)
	yoursLabel.BackgroundTransparency = 1
	yoursLabel.Font = Enum.Font.GothamBold
	yoursLabel.TextSize = 14
	yoursLabel.TextColor3 = GOLD
	yoursLabel.TextXAlignment = Enum.TextXAlignment.Left
	yoursLabel.Text = ""
	yoursLabel.Parent = panel

	listFrame = Instance.new("ScrollingFrame")
	listFrame.Size = UDim2.new(1, -24, 1, -100)
	listFrame.Position = UDim2.fromOffset(12, 72)
	listFrame.BackgroundTransparency = 1
	listFrame.BorderSizePixel = 0
	listFrame.ScrollBarThickness = 5
	listFrame.AutomaticCanvasSize = Enum.AutomaticSize.Y
	listFrame.CanvasSize = UDim2.new()
	listFrame.Parent = panel

	local layout = Instance.new("UIListLayout")
	layout.Padding = UDim.new(0, 4)
	layout.SortOrder = Enum.SortOrder.LayoutOrder
	layout.Parent = listFrame

	local footer = Instance.new("TextLabel")
	footer.Size = UDim2.new(1, -24, 0, 18)
	footer.Position = UDim2.new(0, 12, 1, -24)
	footer.BackgroundTransparency = 1
	footer.Font = Enum.Font.Gotham
	footer.TextSize = 12
	footer.TextColor3 = MUTED
	footer.TextXAlignment = Enum.TextXAlignment.Left
	footer.Text = L.text("board.resets")
	footer.Parent = panel

	renderTabs()
end

function LeaderboardController.init()
	buildUi()

	Remotes.event(Remotes.Names.ClassResult).OnClientEvent:Connect(function(result: any)
		if result.action == "board" and result.ok then
			render(result.payload)
		end
	end)
end

return LeaderboardController
