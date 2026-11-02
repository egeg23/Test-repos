--!strict
--- The shop: passes, one-off products, and the ad rewards.
---
--- Nothing here decides anything. What is owned, what is configured, whether
--- this player may see ads or the paid box -- all of it arrives from the
--- server. A player PolicyService does not allow ads gets an empty ad list, so
--- the ad section is not drawn at all: no heading, no greyed-out button.

local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Remotes = require(ReplicatedStorage.Shared.Remotes)
local L = require(script.Parent.Parent.Locale)
local Ui = require(script.Parent.Parent.Ui)
local BoxController = require(script.Parent.BoxController)
local HudController = require(script.Parent.HudController)

local ShopController = {}

local panel: Frame
local body: ScrollingFrame

local function entry(order: number, titleKey: string, descKey: string?, buttonText: string, colour: string, onPress: (() -> ())?)
	local frame = Instance.new("Frame")
	frame.LayoutOrder = order
	frame.Size = UDim2.new(1, -8, 0, 0)
	frame.AutomaticSize = Enum.AutomaticSize.Y
	frame.BackgroundColor3 = Color3.new(1, 1, 1)
	frame.Parent = body
	Ui.corner(frame, 12)
	Ui.padding(frame, 10)
	Ui.list(frame, 4)
	local title = Ui.label(frame, L.text(titleKey), 20, "ink")
	title.TextXAlignment = Enum.TextXAlignment.Left
	if descKey ~= nil then
		local desc = Ui.label(frame, L.text(descKey), 15, "muted")
		desc.TextXAlignment = Enum.TextXAlignment.Left
		desc.AutomaticSize = Enum.AutomaticSize.Y
	end
	local button = Ui.button(frame, buttonText, colour)
	button.Size = UDim2.new(1, 0, 0, 42)
	button.Active = onPress ~= nil
	if onPress ~= nil then
		button.Activated:Connect(onPress)
	end
end

local function heading(order: number, key: string)
	local label = Ui.label(body, L.text(key), 22, "ink")
	label.LayoutOrder = order
end

local function rebuild(shop: { [string]: any })
	Ui.clear(body)
	local order = 1
	heading(order, "shop.passes")
	for _, pass in shop.passes do
		order += 1
		if pass.owned then
			entry(order, `pass.{pass.id}`, `pass.{pass.id}.desc`, L.text("shop.owned"), "good", nil)
		elseif not pass.configured then
			entry(order, `pass.{pass.id}`, `pass.{pass.id}.desc`, L.text("shop.soon"), "disabled", nil)
		else
			entry(order, `pass.{pass.id}`, `pass.{pass.id}.desc`, L.text("common.robux", pass.robux), "button", function()
				Remotes.event(Remotes.Names.PromptPurchase):FireServer("pass", pass.id)
			end)
		end
	end

	order += 1
	heading(order, "shop.products")
	for _, product in shop.products do
		order += 1
		if not product.configured then
			entry(order, `product.{product.id}`, `product.{product.id}.desc`, L.text("shop.soon"), "disabled", nil)
		elseif product.paidBox ~= nil then
			-- The paid box is bought from the box machine, where its odds are
			-- printed on the same card as the button. Pointing there rather than
			-- selling it here keeps the odds and the purchase together.
			entry(order, `product.{product.id}`, `product.{product.id}.desc`, L.text("box.machine"), "ad", function()
				panel.Visible = false
				BoxController.open()
			end)
		else
			entry(order, `product.{product.id}`, `product.{product.id}.desc`, L.text("common.robux", product.robux), "button", function()
				Remotes.event(Remotes.Names.PromptPurchase):FireServer("product", product.id)
			end)
		end
	end

	if #shop.ads > 0 then
		order += 1
		heading(order, "shop.ads")
		for _, ad in shop.ads do
			order += 1
			local text: string
			local onPress: (() -> ())? = nil
			if ad.usedToday >= ad.dailyLimit then
				text = L.text("ad.limit")
			elseif ad.cooldownLeft > 0 then
				text = L.text("ad.cooldown", Ui.clock(ad.cooldownLeft))
			elseif ad.available then
				text = L.text("ad.watch")
				onPress = function()
					Remotes.event(Remotes.Names.RequestAd):FireServer(ad.id)
				end
			else
				text = L.text("shop.soon")
			end
			entry(order, `ad.{ad.id}`, nil, text, if onPress ~= nil then "ad" else "disabled", onPress)
		end
	end
end

function ShopController.open()
	panel.Visible = true
	Ui.clear(body)
	task.spawn(function()
		local ok, shop = pcall(function()
			return Remotes.func(Remotes.Names.GetShop):InvokeServer()
		end)
		if ok and shop ~= nil and panel.Visible then
			rebuild(shop)
		end
	end)
end

function ShopController.init()
	local gui = Ui.screen("Shop", 4)
	panel, body = Ui.panel(gui, L.text("shop.title"), 460, 620)
	HudController.addButton("hud.shop", 2, function()
		if panel.Visible then
			panel.Visible = false
		else
			ShopController.open()
		end
	end)
	Remotes.event(Remotes.Names.AdState).OnClientEvent:Connect(function()
		if panel.Visible then
			ShopController.open()
		end
	end)
end

return ShopController
