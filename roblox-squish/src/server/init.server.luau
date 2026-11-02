--!strict
--- Server entry point.
---
--- Start order matters. DataService owns profile loading and everything reads
--- through it. PurchaseService must run before the services that register
--- grants on it (ads, shop). SquishService must run before the services that
--- hook into it (theft, traps). A player gets a base only after their profile
--- has loaded, so nobody ever stands in a base the server knows nothing about.

local Analytics = require(script.Services.AnalyticsService)
local DataService = require(script.Services.DataService)
local PolicyCache = require(script.Services.PolicyCache)
local PurchaseService = require(script.Services.PurchaseService)
local PlotService = require(script.Services.PlotService)
local SquishService = require(script.Services.SquishService)
local MovementGuard = require(script.Services.MovementGuard)
local TrapService = require(script.Services.TrapService)
local StealService = require(script.Services.StealService)
local BoxService = require(script.Services.BoxService)
local AdService = require(script.Services.AdService)
local ShopService = require(script.Services.ShopService)
local ShowService = require(script.Services.ShowService)
local TradeService = require(script.Services.TradeService)

Analytics.start()
PolicyCache.start()
PlotService.start()
DataService.start()
DataService.ProfileLoaded:Connect(Analytics.playerJoined)
PurchaseService.start()
SquishService.start()
MovementGuard.start()
TrapService.start()
StealService.start()
BoxService.start()
AdService.start()
ShopService.start()
ShowService.start()
TradeService.start()

-- Last, so every service above has connected to ProfileLoaded first and has
-- seen the profile before the base appears.
DataService.ProfileLoaded:Connect(function(player: Player)
	PlotService.claim(player)
end)

print("[squish] server ready")
