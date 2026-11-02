--!strict
--- Client entry point.
---
--- The HUD comes first: the panels register their buttons on it. State starts
--- listening before anything else draws, so the first State message from the
--- server is never missed.

local State = require(script.State)
local HudController = require(script.Controllers.HudController)
local WorldController = require(script.Controllers.WorldController)
local BoxController = require(script.Controllers.BoxController)
local BaseController = require(script.Controllers.BaseController)
local ShopController = require(script.Controllers.ShopController)
local ShowController = require(script.Controllers.ShowController)
local TradeController = require(script.Controllers.TradeController)
local OnboardingController = require(script.Controllers.OnboardingController)

State.init()
HudController.init()
WorldController.init()
BoxController.init()
BaseController.init()
ShopController.init()
ShowController.init()
TradeController.init()
OnboardingController.init()

print("[squish] client ready")
