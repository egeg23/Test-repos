--!strict
--- Client entry point.

local ClassController = require(script.Controllers.ClassController)
local CourseBuilderController = require(script.Controllers.CourseBuilderController)
local LessonController = require(script.Controllers.LessonController)
local ObstacleController = require(script.Controllers.ObstacleController)

LessonController.init()
ObstacleController.init()
-- Built before ClassController, which opens it from the teacher panel.
CourseBuilderController.init()
ClassController.init()

print("[school] client ready")
