--!strict
--- Trading: pick a player, both build an offer, both confirm.
---
--- The window shows both offers side by side at all times. When either offer
--- changes, both confirmations clear on the server and the buttons here say
--- so; there is no way to confirm one deal and receive another.

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Remotes = require(ReplicatedStorage.Shared.Remotes)
local Trade = require(ReplicatedStorage.Shared.Config.Trade)
local L = require(script.Parent.Parent.Locale)
local State = require(script.Parent.Parent.State)
local Ui = require(script.Parent.Parent.Ui)
local HudController = require(script.Parent.HudController)

local TradeController = {}

local panel: Frame
local body: ScrollingFrame
local session: { [string]: any }? = nil
local myOffer: { string } = {}

local function send(action: string, extra: { [string]: any }?)
	local request: { [string]: any } = { action = action }
	for key, value in extra or {} do
		request[key] = value
	end
	Remotes.event(Remotes.Names.TradeAction):FireServer(request)
end

local function itemLine(parent: Instance, item: { [string]: any }, order: number)
	local line = Ui.label(parent, `{L.text(`squish.{item.species}`)} · {L.text("common.tier", item.tier)}`, 17, "ink")
	line.LayoutOrder = order
	line.TextXAlignment = Enum.TextXAlignment.Left
end

local function pickPlayer()
	Ui.clear(body)
	local title = Ui.label(body, L.text("trade.pick"), 22, "ink")
	title.LayoutOrder = 1
	local any = false
	for index, other in Players:GetPlayers() do
		if other ~= Players.LocalPlayer then
			any = true
			local button = Ui.button(body, other.DisplayName, "button")
			button.LayoutOrder = 1 + index
			button.Size = UDim2.new(1, -8, 0, 44)
			button.Activated:Connect(function()
				send("request", { userId = other.UserId })
			end)
		end
	end
	if not any then
		local empty = Ui.label(body, L.text("trade.nobody"), 16, "muted")
		empty.LayoutOrder = 2
	end
end

local function drawSession(current: { [string]: any })
	Ui.clear(body)
	if current.state == "requested" then
		if current.incoming then
			local ask = Ui.label(body, L.text("trade.request", current.partner), 22, "ink")
			ask.LayoutOrder = 1
			local yes = Ui.button(body, L.text("trade.accept"), "good")
			yes.LayoutOrder = 2
			yes.Activated:Connect(function()
				send("accept")
			end)
			local no = Ui.button(body, L.text("trade.decline"), "disabled")
			no.LayoutOrder = 3
			no.Activated:Connect(function()
				send("cancel")
			end)
		else
			local wait = Ui.label(body, L.text("trade.waiting"), 20, "muted")
			wait.LayoutOrder = 1
			local cancel = Ui.button(body, L.text("common.cancel"), "disabled")
			cancel.LayoutOrder = 2
			cancel.Activated:Connect(function()
				send("cancel")
			end)
		end
		return
	end

	myOffer = {}
	for _, item in current.mine do
		table.insert(myOffer, item.uid)
	end

	local order = 1
	local mineTitle = Ui.label(body, L.text("trade.yours"), 20, "ink")
	mineTitle.LayoutOrder = order
	for _, item in current.mine do
		order += 1
		itemLine(body, item, order)
	end
	order += 1
	local theirsTitle = Ui.label(body, `{L.text("trade.theirs")} · {current.partner}`, 20, "ink")
	theirsTitle.LayoutOrder = order
	for _, item in current.theirs do
		order += 1
		itemLine(body, item, order)
	end

	order += 1
	if current.state == "countdown" then
		local countdown = Ui.label(body, L.text("trade.countdown", Trade.ConfirmCountdown), 22, "ink")
		countdown.LayoutOrder = order
	else
		local confirm = Ui.button(body, if current.myConfirm then L.text("trade.waiting") else L.text("trade.confirm"), if current.myConfirm then "disabled" else "good")
		confirm.LayoutOrder = order
		confirm.Size = UDim2.new(1, -8, 0, 46)
		confirm.Activated:Connect(function()
			send("confirm")
		end)
	end
	order += 1
	local cancel = Ui.button(body, L.text("common.cancel"), "disabled")
	cancel.LayoutOrder = order
	cancel.Size = UDim2.new(1, -8, 0, 40)
	cancel.Activated:Connect(function()
		send("cancel")
	end)

	-- My collection, to add to or take from the offer.
	local state = State.current
	if state == nil then
		return
	end
	order += 1
	local pickTitle = Ui.label(body, L.text("base.title"), 18, "muted")
	pickTitle.LayoutOrder = order
	for _, squish in state.squishes do
		if squish.inTransit then
			continue
		end
		order += 1
		local offered = table.find(myOffer, squish.uid) ~= nil
		local text = `{if offered then "✓ " else ""}{L.text(`squish.{squish.species}`)} · {L.text("common.tier", squish.tier)}`
		local button = Ui.button(body, text, if offered then "good" else "button")
		button.LayoutOrder = order
		button.Size = UDim2.new(1, -8, 0, 38)
		button.TextSize = 16
		button.Activated:Connect(function()
			local next = table.clone(myOffer)
			local at = table.find(next, squish.uid)
			if at ~= nil then
				table.remove(next, at)
			elseif #next < Trade.MaxItemsPerSide then
				table.insert(next, squish.uid)
			end
			send("offer", { uids = next })
		end)
	end
end

function TradeController.init()
	local gui = Ui.screen("Trade", 4)
	panel, body = Ui.panel(gui, L.text("trade.title"), 460, 620)
	HudController.addButton("hud.trade", 4, function()
		if panel.Visible then
			panel.Visible = false
			return
		end
		panel.Visible = true
		local current = session
		if current ~= nil then
			drawSession(current)
		else
			pickPlayer()
		end
	end)
	Remotes.event(Remotes.Names.TradeState).OnClientEvent:Connect(function(state)
		session = state
		if state == nil then
			if panel.Visible then
				pickPlayer()
			end
			return
		end
		panel.Visible = true
		drawSession(state)
	end)
end

return TradeController
