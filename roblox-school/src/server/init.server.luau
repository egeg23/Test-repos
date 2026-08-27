--!strict
--- Server entry point.
---
--- Start order matters: DataService owns profile loading, and every other
--- service reads through it. PurchaseService must be running before AdService,
--- which registers its rewards as grants on it. AchievementService must be
--- running before PayoutService, because draining a teacher's queue applies the
--- counters it carries.

local Analytics = require(script.Services.AnalyticsService)
local DataService = require(script.Services.DataService)
local PurchaseService = require(script.Services.PurchaseService)
local AdService = require(script.Services.AdService)
local AchievementService = require(script.Services.AchievementService)
local PayoutService = require(script.Services.PayoutService)
local ClassService = require(script.Services.ClassService)
local ShopService = require(script.Services.ShopService)
local AssemblyService = require(script.Services.AssemblyService)
local ObstacleService = require(script.Services.ObstacleService)
local MatchmakingSignalsService = require(script.Services.MatchmakingSignalsService)
local LessonService = require(script.Services.LessonService)
local LiveLessonService = require(script.Services.LiveLessonService)
local WorldService = require(script.Services.WorldService)

Analytics.start()
DataService.start()
DataService.ProfileLoaded:Connect(Analytics.playerJoined)

-- Logging in counts as being present, so a student who plays other subjects for
-- a fortnight does not lose the seat they are still using.
DataService.ProfileLoaded:Connect(function(player, data)
	local classId = data.enrolledClassId
	if classId ~= nil then
		task.spawn(ClassService.touchMember, player, classId)
	end
end)
PurchaseService.start()
AchievementService.start()
PayoutService.start()
ShopService.start()
AdService.start()
ClassService.start()
ObstacleService.start()
AssemblyService.start()
LessonService.start()
LiveLessonService.start()
MatchmakingSignalsService.start()
WorldService.start()

print("[school] server ready")
