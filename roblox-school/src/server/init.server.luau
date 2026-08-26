--!strict
--- Server entry point.
---
--- Start order matters: DataService owns profile loading, and every other
--- service reads through it. PurchaseService must be running before AdService,
--- which registers its rewards as grants on it.

local Analytics = require(script.Services.AnalyticsService)
local DataService = require(script.Services.DataService)
local PurchaseService = require(script.Services.PurchaseService)
local AdService = require(script.Services.AdService)
local PayoutService = require(script.Services.PayoutService)
local ClassService = require(script.Services.ClassService)
local ShopService = require(script.Services.ShopService)
local AssemblyService = require(script.Services.AssemblyService)
local ObstacleService = require(script.Services.ObstacleService)
local MatchmakingSignalsService = require(script.Services.MatchmakingSignalsService)
local LessonService = require(script.Services.LessonService)
local LiveLessonService = require(script.Services.LiveLessonService)

Analytics.start()
DataService.start()
DataService.ProfileLoaded:Connect(Analytics.playerJoined)
PurchaseService.start()
PayoutService.start()
ShopService.start()
AdService.start()
ClassService.start()
ObstacleService.start()
AssemblyService.start()
LessonService.start()
LiveLessonService.start()
MatchmakingSignalsService.start()

print("[school] server ready")
