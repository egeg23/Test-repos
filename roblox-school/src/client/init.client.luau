--!strict
--- Client entry point.

local CampusController = require(script.Controllers.CampusController)
local ClassController = require(script.Controllers.ClassController)
local CourseBuilderController = require(script.Controllers.CourseBuilderController)
local LessonController = require(script.Controllers.LessonController)
local ObstacleController = require(script.Controllers.ObstacleController)
local QuestionEditorController = require(script.Controllers.QuestionEditorController)

LessonController.init()
ObstacleController.init()
-- Both are built before ClassController, which opens them from the teacher panel.
CourseBuilderController.init()
QuestionEditorController.init()
ClassController.init()
CampusController.init()

print("[school] client ready")
