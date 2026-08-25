--!strict
--- Server entry point.
---
--- Start order matters: DataService owns profile loading, and every other
--- service reads through it. PurchaseService must be running before AdService,
--- which registers its rewards as grants on it.

local DataService = require(script.Services.DataService)
local PurchaseService = require(script.Services.PurchaseService)
local AdService = require(script.Services.AdService)
local PayoutService = require(script.Services.PayoutService)
local ClassService = require(script.Services.ClassService)
local ShopService = require(script.Services.ShopService)
local LessonService = require(script.Services.LessonService)

DataService.start()
PurchaseService.start()
PayoutService.start()
ShopService.start()
AdService.start()
ClassService.start()
LessonService.start()

print("[school] server ready")
