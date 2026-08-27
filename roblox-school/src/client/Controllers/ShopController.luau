--!strict
--- The shop: passes, consumables, and the rewards an ad buys.
---
--- This is the entry point the whole monetization was missing. Every other piece
--- existed -- the configured products, the receipt handling, the grants, the ad
--- flow -- with nothing anywhere that a player could press to start any of it.
---
--- Nothing here decides anything. Ownership, availability, cooldowns and quotas
--- all arrive from the server; a button that looks purchasable is a button the
--- server has already said is purchasable, and pressing one it has not will be
--- refused there anyway.

local MarketplaceService = game:GetService("MarketplaceService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Monetization = require(ReplicatedStorage.Shared.Config.Monetization)
local Remotes = require(ReplicatedStorage.Shared.Remotes)
local L = require(script.Parent.Parent.Locale)

local ShopController = {}

local player = Players.LocalPlayer

local PANEL = Color3.fromRGB(28, 30, 38)
local ROW = Color3.fromRGB(44, 48, 58)
local ACCENT = Color3.fromRGB(70, 96, 190)
local OWNED = Color3.fromRGB(64, 120, 92)
local AD = Color3.fromRGB(150, 110, 60)
local DISABLED = Color3.fromRGB(58, 62, 72)
local TEXT = Color3.fromRGB(236, 238, 244)
local MUTED = Color3.fromRGB(150, 156, 170)

local panel: Frame
local listFrame: ScrollingFrame
local balanceLabel: TextLabel

local owned: { [string]: boolean } = {}
local licensed = false
local ads: { any } = {}

local function corner(instance: Instance, radius: number)
	local ui = Instance.new("UICorner")
	ui.CornerRadius = UDim.new(0, radius)
	ui.Parent = instance
end

local function send(action: string)
	Remotes.event(Remotes.Names.ClassAction):FireServer({ action = action })
end

local function clearList()
	for _, child in listFrame:GetChildren() do
		if child:IsA("GuiObject") then
			child:Destroy()
		end
	end
end

local function heading(key: string)
	local label = Instance.new("TextLabel")
	label.Size = UDim2.new(1, -8, 0, 28)
	label.BackgroundTransparency = 1
	label.Font = Enum.Font.GothamBold
	label.TextSize = 13
	label.TextColor3 = MUTED
	label.TextXAlignment = Enum.TextXAlignment.Left
	label.Text = string.upper(L.text(key))
	label.Parent = listFrame
end

local function entry(titleKey: string, subtitle: string, buttonText: string, colour: Color3): TextButton
	local row = Instance.new("Frame")
	row.Size = UDim2.new(1, -8, 0, 52)
	row.BackgroundColor3 = ROW
	row.BorderSizePixel = 0
	row.Parent = listFrame
	corner(row, 8)

	local title = Instance.new("TextLabel")
	title.Size = UDim2.new(1, -140, 0, 20)
	title.Position = UDim2.fromOffset(10, 6)
	title.BackgroundTransparency = 1
	title.Font = Enum.Font.GothamMedium
	title.TextSize = 15
	title.TextColor3 = TEXT
	title.TextXAlignment = Enum.TextXAlignment.Left
	title.TextTruncate = Enum.TextTruncate.AtEnd
	title.Text = L.text(titleKey)
	title.Parent = row

	local meta = Instance.new("TextLabel")
	meta.Size = UDim2.new(1, -140, 0, 18)
	meta.Position = UDim2.fromOffset(10, 27)
	meta.BackgroundTransparency = 1
	meta.Font = Enum.Font.Gotham
	meta.TextSize = 12
	meta.TextColor3 = MUTED
	meta.TextXAlignment = Enum.TextXAlignment.Left
	meta.Text = subtitle
	meta.Parent = row

	local button = Instance.new("TextButton")
	button.Size = UDim2.fromOffset(118, 32)
	button.Position = UDim2.new(1, -128, 0, 10)
	button.BackgroundColor3 = colour
	button.BorderSizePixel = 0
	button.Font = Enum.Font.GothamBold
	button.TextSize = 14
	button.TextColor3 = TEXT
	button.Text = buttonText
	button.Parent = row
	corner(button, 6)
	return button
end

--- Audience filter. A student is not shown a class-capacity pass, and a teacher
--- still sees the student ones because they were a student first and their
--- progress did not stop mattering.
local function shows(audience: string): boolean
	return audience == "student" or licensed
end

local function render()
	clearList()

	heading("shop.passes")
	for _, pass in Monetization.Passes do
		if not shows(pass.audience) then
			continue
		end

		local isOwned = owned[pass.id] == true
		local configured = pass.gamePassId ~= 0
		local caption = if isOwned
			then L.text("shop.owned")
			elseif not configured then L.text("shop.notConfigured")
			else L.text("shop.buy")
		local colour = if isOwned then OWNED elseif not configured then DISABLED else ACCENT

		local button = entry(pass.displayKey, `{pass.robux} R$`, caption, colour)
		button.Active = not isOwned and configured
		button.AutoButtonColor = button.Active
		button.Activated:Connect(function()
			if isOwned or not configured then
				return
			end
			MarketplaceService:PromptGamePassPurchase(player, pass.gamePassId)
		end)
	end

	heading("shop.products")
	for _, product in Monetization.Products do
		if not shows(product.audience) then
			continue
		end

		local configured = product.devProductId ~= 0
		local button = entry(
			product.displayKey,
			`{product.robux} R$`,
			if configured then L.text("shop.buy") else L.text("shop.notConfigured"),
			if configured then ACCENT else DISABLED
		)
		button.Active = configured
		button.AutoButtonColor = configured
		button.Activated:Connect(function()
			if not configured then
				return
			end
			MarketplaceService:PromptProductPurchase(player, product.devProductId)
		end)
	end

	-- An empty ad list is what a player under 13 gets: the section is simply not
	-- drawn. A disabled ad button would still be an ad button.
	if #ads == 0 then
		return
	end

	heading("shop.ads")
	local drawn = 0
	for _, reward in ads do
		if not shows(reward.audience) then
			continue
		end
		drawn += 1

		local subtitle = L.text("shop.usedToday", reward.usedToday, reward.dailyLimit)
		if not reward.available and reward.cooldownLeft > 0 then
			subtitle = `{subtitle} · `
				.. L.text("shop.cooldown", math.ceil(reward.cooldownLeft / 60))
		end

		local button = entry(
			`ad.{reward.id}`,
			subtitle,
			L.text("shop.watch"),
			if reward.available then AD else DISABLED
		)
		button.Active = reward.available
		button.AutoButtonColor = reward.available
		button.Activated:Connect(function()
			if not reward.available then
				return
			end
			Remotes.event(Remotes.Names.RequestAd):FireServer(reward.id)
		end)
	end

	if drawn == 0 then
		local label = Instance.new("TextLabel")
		label.Size = UDim2.new(1, -8, 0, 30)
		label.BackgroundTransparency = 1
		label.Font = Enum.Font.Gotham
		label.TextSize = 13
		label.TextColor3 = MUTED
		label.TextXAlignment = Enum.TextXAlignment.Left
		label.Text = L.text("shop.noAds")
		label.Parent = listFrame
	end
end

local function buildUi()
	local gui = Instance.new("ScreenGui")
	gui.Name = "ShopGui"
	gui.ResetOnSpawn = false
	gui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
	gui.Parent = player:WaitForChild("PlayerGui")

	local toggle = Instance.new("TextButton")
	toggle.Size = UDim2.fromOffset(120, 36)
	toggle.Position = UDim2.fromOffset(272, 16)
	toggle.BackgroundColor3 = ACCENT
	toggle.BorderSizePixel = 0
	toggle.Font = Enum.Font.GothamBold
	toggle.TextSize = 16
	toggle.TextColor3 = TEXT
	toggle.Text = L.text("shop.title")
	toggle.Parent = gui
	corner(toggle, 8)

	panel = Instance.new("Frame")
	panel.Size = UDim2.fromScale(0.4, 0.66)
	panel.Position = UDim2.fromScale(0.55, 0.16)
	panel.BackgroundColor3 = PANEL
	panel.BorderSizePixel = 0
	panel.Visible = false
	panel.Parent = gui
	corner(panel, 12)

	toggle.Activated:Connect(function()
		panel.Visible = not panel.Visible
		if panel.Visible then
			ShopController.refresh()
		end
	end)

	balanceLabel = Instance.new("TextLabel")
	balanceLabel.Size = UDim2.new(1, -24, 0, 26)
	balanceLabel.Position = UDim2.fromOffset(12, 12)
	balanceLabel.BackgroundTransparency = 1
	balanceLabel.Font = Enum.Font.GothamBold
	balanceLabel.TextSize = 16
	balanceLabel.TextColor3 = TEXT
	balanceLabel.TextXAlignment = Enum.TextXAlignment.Left
	balanceLabel.Text = ""
	balanceLabel.Parent = panel

	listFrame = Instance.new("ScrollingFrame")
	listFrame.Size = UDim2.new(1, -24, 1, -54)
	listFrame.Position = UDim2.fromOffset(12, 44)
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
end

function ShopController.refresh()
	send("shop")
	send("ads")
end

function ShopController.init()
	buildUi()

	Remotes.event(Remotes.Names.ClassResult).OnClientEvent:Connect(function(result: any)
		if result.action == "shop" and result.ok then
			owned = result.payload.owned or {}
			licensed = result.payload.licensed == true
			balanceLabel.Text = L.text("shop.balance", result.payload.points or 0)
			render()
		elseif result.action == "ads" and result.ok then
			ads = result.payload or {}
			render()
		end
	end)

	-- A watched ad changes a quota and a cooldown, so the panel is stale the
	-- moment one finishes.
	Remotes.event(Remotes.Names.AdState).OnClientEvent:Connect(function()
		if panel.Visible then
			ShopController.refresh()
		end
	end)

	MarketplaceService.PromptGamePassPurchaseFinished:Connect(function()
		if panel.Visible then
			ShopController.refresh()
		end
	end)
end

return ShopController
