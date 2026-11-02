--!strict
--- The base panel: every squish you own, shelves and pocket, and the traps.
---
--- Each row is a squish with what can be done to it right now: merge when it
--- has a twin, move between shelf and pocket, sell. Favourites carry a star,
--- because they cannot be stolen and a player should know which ones those are.

local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Economy = require(ReplicatedStorage.Shared.Config.Economy)
local Remotes = require(ReplicatedStorage.Shared.Remotes)
local Squishes = require(ReplicatedStorage.Shared.Config.Squishes)
local Traps = require(ReplicatedStorage.Shared.Config.Traps)
local L = require(script.Parent.Parent.Locale)
local State = require(script.Parent.Parent.State)
local Ui = require(script.Parent.Parent.Ui)
local HudController = require(script.Parent.HudController)

local BaseController = {}

local panel: Frame
local body: ScrollingFrame

local function send(action: string, extra: { [string]: any }?)
	local request: { [string]: any } = { action = action }
	for key, value in extra or {} do
		request[key] = value
	end
	Remotes.event(Remotes.Names.BaseAction):FireServer(request)
end

local function hasTwin(list: { any }, entry: any): boolean
	if entry.tier >= Economy.MaxTier then
		return false
	end
	for _, other in list do
		if other.uid ~= entry.uid and other.species == entry.species and other.tier == entry.tier and not other.inTransit then
			return true
		end
	end
	return false
end

local function row(list: { any }, entry: any, order: number)
	local species = Squishes.get(entry.species)
	local frame = Instance.new("Frame")
	frame.LayoutOrder = order
	frame.Size = UDim2.new(1, -8, 0, 0)
	frame.AutomaticSize = Enum.AutomaticSize.Y
	frame.BackgroundColor3 = Color3.new(1, 1, 1)
	frame.Parent = body
	Ui.corner(frame, 12)
	Ui.padding(frame, 8)
	if species ~= nil then
		Ui.stroke(frame, Ui.rarityColour(species.rarity), 2)
	end
	Ui.list(frame, 4)

	local star = if entry.favourite then "★ " else ""
	local title = Ui.label(frame, `{star}{L.text(`squish.{entry.species}`)} · {L.text("common.tier", entry.tier)}`, 20, "ink")
	title.TextXAlignment = Enum.TextXAlignment.Left
	if species ~= nil then
		local sub = Ui.label(frame, `{L.text(`rarity.{species.rarity}`)} · {L.text("common.perSecond", Ui.short(Economy.incomePerSecond(species.rarity, entry.tier)))}`, 15, "muted")
		sub.TextXAlignment = Enum.TextXAlignment.Left
	end

	local actions = Instance.new("Frame")
	actions.BackgroundTransparency = 1
	actions.Size = UDim2.new(1, 0, 0, 40)
	actions.Parent = frame
	local layout = Ui.list(actions, 6, true)
	layout.HorizontalAlignment = Enum.HorizontalAlignment.Left

	local function action(text: string, colour: string, onPress: () -> ())
		local button = Ui.button(actions, text, colour)
		button.Size = UDim2.new(0, 0, 1, 0)
		button.AutomaticSize = Enum.AutomaticSize.X
		button.TextSize = 16
		Ui.padding(button, 8)
		button.Activated:Connect(onPress)
	end

	if entry.inTransit then
		return
	end
	if hasTwin(list, entry) then
		action(L.text("base.merge"), "good", function()
			send("merge", { uid = entry.uid })
		end)
	end
	if entry.slot == nil then
		action(L.text("base.place"), "button", function()
			send("place", { uid = entry.uid })
		end)
	else
		action(L.text("base.store"), "button", function()
			send("store", { uid = entry.uid })
		end)
	end
	action(L.text("base.sell", Ui.short(entry.resale)), "disabled", function()
		send("sell", { uid = entry.uid })
	end)
end

local function trapsSection(state: { [string]: any }, order: number)
	local heading = Ui.label(body, L.text("trap.title"), 22, "ink")
	heading.LayoutOrder = order
	local note = Ui.label(body, L.text("trap.note"), 14, "muted")
	note.LayoutOrder = order + 1
	note.AutomaticSize = Enum.AutomaticSize.Y
	for index, trap in Traps.List do
		local level = (state.traps or {})[trap.id] or 0
		local frame = Instance.new("Frame")
		frame.LayoutOrder = order + 1 + index
		frame.Size = UDim2.new(1, -8, 0, 0)
		frame.AutomaticSize = Enum.AutomaticSize.Y
		frame.BackgroundColor3 = Color3.fromRGB(trap.colour[1], trap.colour[2], trap.colour[3]):Lerp(Color3.new(1, 1, 1), 0.6)
		frame.Parent = body
		Ui.corner(frame, 12)
		Ui.padding(frame, 8)
		Ui.list(frame, 4)
		local title = Ui.label(frame, `{L.text(`trap.{trap.id}`)} · {L.text("trap.level", level)}`, 20, "ink")
		title.TextXAlignment = Enum.TextXAlignment.Left
		local desc = Ui.label(frame, L.text(`trap.{trap.id}.desc`), 14, "muted")
		desc.TextXAlignment = Enum.TextXAlignment.Left
		desc.AutomaticSize = Enum.AutomaticSize.Y
		local cost = Traps.nextCost(trap, level)
		local text = if cost == nil
			then L.text("trap.max")
			elseif level == 0 then L.text("trap.build", L.text("common.coins", Ui.short(cost)))
			else L.text("trap.upgrade", L.text("common.coins", Ui.short(cost)))
		local button = Ui.button(frame, text, if cost == nil then "disabled" else "good")
		button.Size = UDim2.new(1, 0, 0, 40)
		button.Active = cost ~= nil
		button.Activated:Connect(function()
			if cost ~= nil then
				send("upgradeTrap", { trap = trap.id })
			end
		end)
	end
end

local function rebuild()
	local state = State.current
	if state == nil or not panel.Visible then
		return
	end
	Ui.clear(body)

	local shelved, pocket = {}, {}
	for _, entry in state.squishes do
		if entry.slot ~= nil or entry.inTransit then
			table.insert(shelved, entry)
		else
			table.insert(pocket, entry)
		end
	end
	local function byValue(a, b)
		local sa, sb = Squishes.get(a.species), Squishes.get(b.species)
		local ia = if sa then Economy.incomePerSecond(sa.rarity, a.tier) else 0
		local ib = if sb then Economy.incomePerSecond(sb.rarity, b.tier) else 0
		return ia > ib
	end
	table.sort(shelved, byValue)
	table.sort(pocket, byValue)

	local summary = Ui.label(body, L.text("base.slots", #shelved, state.slots), 20, "ink")
	summary.LayoutOrder = 1
	local hint = Ui.label(body, L.text("base.mergeHint"), 14, "muted")
	hint.LayoutOrder = 2
	hint.AutomaticSize = Enum.AutomaticSize.Y
	local slotButton = Ui.button(
		body,
		if state.nextSlotCost ~= nil then L.text("base.buySlot", L.text("common.coins", Ui.short(state.nextSlotCost))) else L.text("base.slotsMax"),
		if state.nextSlotCost ~= nil then "good" else "disabled"
	)
	slotButton.LayoutOrder = 3
	slotButton.Size = UDim2.new(1, -8, 0, 44)
	slotButton.Activated:Connect(function()
		if state.nextSlotCost ~= nil then
			send("buySlot")
		end
	end)

	local order = 10
	for _, entry in shelved do
		row(state.squishes, entry, order)
		order += 1
	end
	local pocketTitle = Ui.label(body, L.text("base.pocket"), 22, "ink")
	pocketTitle.LayoutOrder = order
	order += 1
	if #pocket == 0 then
		local empty = Ui.label(body, L.text("base.pocketEmpty"), 16, "muted")
		empty.LayoutOrder = order
		order += 1
	end
	for _, entry in pocket do
		row(state.squishes, entry, order)
		order += 1
	end
	trapsSection(state, order + 10)
end

function BaseController.open()
	panel.Visible = true
	rebuild()
end

function BaseController.init()
	local gui = Ui.screen("Base", 4)
	panel, body = Ui.panel(gui, L.text("base.title"), 480, 640)
	HudController.addButton("hud.base", 1, function()
		if panel.Visible then
			panel.Visible = false
		else
			BaseController.open()
		end
	end)
	State.Changed:Connect(rebuild)
end

return BaseController
