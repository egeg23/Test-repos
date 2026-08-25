--!strict
--- Client entry point.

local ClassController = require(script.Controllers.ClassController)
local LessonController = require(script.Controllers.LessonController)

LessonController.init()
ClassController.init()

print("[school] client ready")
