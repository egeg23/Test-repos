--!strict
--- Funnel and economy events, into Roblox's own analytics.
---
--- The onboarding funnel is the one to watch in a soft launch: what share of
--- arrivals open a box, put a squish on a shelf, squeeze it, and come back for a
--- second box. Every constant in Config was chosen by reasoning, not data, and
--- these events are how the first tuning pass gets data.
---
--- Every call is wrapped: analytics failing is never a reason for a box to fail.

local AnalyticsService = game:GetService("AnalyticsService")
local Players = game:GetService("Players")

local Analytics = {}

local ONBOARDING = {
	joined = 1,
	firstBox = 2,
	firstSqueeze = 3,
	secondBox = 4,
	firstMerge = 5,
}

local reached: { [Player]: { [string]: boolean } } = {}

local function safely(body: () -> ())
	local ok, err = pcall(body)
	if not ok then
		warn(`[squish] analytics call failed: {err}`)
	end
end

local function step(player: Player, name: string)
	local seen = reached[player]
	if seen == nil then
		seen = {}
		reached[player] = seen
	end
	if seen[name] then
		return
	end
	seen[name] = true
	local index = (ONBOARDING :: any)[name] :: number
	safely(function()
		AnalyticsService:LogOnboardingFunnelStepEvent(player, index, name)
	end)
end

function Analytics.playerJoined(player: Player)
	step(player, "joined")
end

function Analytics.boxOpened(player: Player, boxId: string, rarity: string, boxesOpened: number)
	step(player, "firstBox")
	if boxesOpened >= 2 then
		step(player, "secondBox")
	end
	safely(function()
		AnalyticsService:LogCustomEvent(player, "boxOpened", 1, { box = boxId, rarity = rarity })
	end)
end

function Analytics.squeezed(player: Player)
	step(player, "firstSqueeze")
end

function Analytics.merged(player: Player, species: string, tier: number)
	step(player, "firstMerge")
	safely(function()
		AnalyticsService:LogCustomEvent(player, "merged", tier, { species = species })
	end)
end

function Analytics.coins(player: Player, flow: "source" | "sink", amount: number, balance: number, kind: string)
	if amount <= 0 then
		return
	end
	safely(function()
		local flowType = if flow == "source" then Enum.AnalyticsEconomyFlowType.Source else Enum.AnalyticsEconomyFlowType.Sink
		AnalyticsService:LogEconomyEvent(player, flowType, "Coins", math.floor(amount), math.floor(balance), kind)
	end)
end

function Analytics.theft(player: Player, outcome: string)
	safely(function()
		AnalyticsService:LogCustomEvent(player, "theft", 1, { outcome = outcome })
	end)
end

function Analytics.purchase(player: Player, kind: string, id: string, robux: number)
	safely(function()
		AnalyticsService:LogCustomEvent(player, "purchase", robux, { kind = kind, id = id })
	end)
end

function Analytics.adGranted(player: Player, rewardId: string)
	safely(function()
		AnalyticsService:LogCustomEvent(player, "adGranted", 1, { reward = rewardId })
	end)
end

function Analytics.start()
	Players.PlayerRemoving:Connect(function(player: Player)
		reached[player] = nil
	end)
end

return Analytics
