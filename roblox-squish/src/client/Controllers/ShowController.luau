--!strict
--- The weekly Squish Show panel: your score, the top of the week, the prize.

local ProximityPromptService = game:GetService("ProximityPromptService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Remotes = require(ReplicatedStorage.Shared.Remotes)
local L = require(script.Parent.Parent.Locale)
local Ui = require(script.Parent.Parent.Ui)
local HudController = require(script.Parent.HudController)

local ShowController = {}

local panel: Frame
local body: ScrollingFrame

local function rebuild(show: { [string]: any })
	Ui.clear(body)
	local score = Ui.label(body, L.text("show.score", Ui.short(show.score)), 26, "ink")
	score.LayoutOrder = 1
	local how = Ui.label(body, L.text("show.how", show.counted), 15, "muted")
	how.LayoutOrder = 2
	local ends = Ui.label(body, L.text("show.ends", Ui.duration(show.endsIn)), 18, "ink")
	ends.LayoutOrder = 3
	if show.prize ~= nil then
		local prize = Ui.label(body, L.text("show.prize", show.winners, L.text(`squish.{show.prize}`)), 16, "ink")
		prize.LayoutOrder = 4
		prize.AutomaticSize = Enum.AutomaticSize.Y
	end
	local top = Ui.label(body, L.text("show.top"), 22, "ink")
	top.LayoutOrder = 5
	if #show.top == 0 then
		local empty = Ui.label(body, L.text("show.empty"), 16, "muted")
		empty.LayoutOrder = 6
	end
	for index, row in show.top do
		local line = Ui.label(body, `{row.rank}. {row.name}  ·  {Ui.short(row.score)}`, 18, "ink")
		line.LayoutOrder = 10 + index
		line.TextXAlignment = Enum.TextXAlignment.Left
	end
end

function ShowController.open()
	panel.Visible = true
	Ui.clear(body)
	task.spawn(function()
		local ok, show = pcall(function()
			return Remotes.func(Remotes.Names.GetShow):InvokeServer()
		end)
		if ok and show ~= nil and panel.Visible then
			rebuild(show)
		end
	end)
end

function ShowController.init()
	local gui = Ui.screen("Show", 4)
	panel, body = Ui.panel(gui, L.text("show.title"), 440, 560)
	HudController.addButton("hud.show", 3, function()
		if panel.Visible then
			panel.Visible = false
		else
			ShowController.open()
		end
	end)
	ProximityPromptService.PromptTriggered:Connect(function(prompt: ProximityPrompt)
		if prompt.Name == "ShowPrompt" then
			ShowController.open()
		end
	end)
end

return ShowController
