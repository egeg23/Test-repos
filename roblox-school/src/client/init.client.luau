--!strict
--- Client entry point.

local AchievementController = require(script.Controllers.AchievementController)
local HudController = require(script.Controllers.HudController)
local AssemblyController = require(script.Controllers.AssemblyController)
local CampusController = require(script.Controllers.CampusController)
local ClassController = require(script.Controllers.ClassController)
local CourseBuilderController = require(script.Controllers.CourseBuilderController)
local LessonController = require(script.Controllers.LessonController)
local LiveLessonController = require(script.Controllers.LiveLessonController)
local ObstacleController = require(script.Controllers.ObstacleController)
local PromptLabelController = require(script.Controllers.PromptLabelController)
local ShopController = require(script.Controllers.ShopController)
local UniformController = require(script.Controllers.UniformController)
local QuestionEditorController = require(script.Controllers.QuestionEditorController)

-- The HUD owns the toolbar every panel registers a button on, so it is built
-- before any of them.
HudController.init()
LessonController.init()
ObstacleController.init()
AssemblyController.init()
LiveLessonController.init()
-- Both are built before ClassController, which opens them from the teacher panel.
CourseBuilderController.init()
QuestionEditorController.init()
ClassController.init()
CampusController.init()
ShopController.init()
AchievementController.init()
UniformController.init()
PromptLabelController.init()

print("[school] client ready")
