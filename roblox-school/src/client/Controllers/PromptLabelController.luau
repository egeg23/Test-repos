--!strict
--- Labels the classroom prompts in the player's own language.
---
--- Done on the client because a ProximityPrompt is a replicated instance: its
--- text is one value shared by everyone on the server, so writing a language
--- into it from the server writes that language for the whole room. Property
--- changes made on a client stay on that client, which is exactly what is wanted
--- here.

local CollectionService = game:GetService("CollectionService")

local L = require(script.Parent.Parent.Locale)

local PromptLabelController = {}

local TAG = "SubjectPrompt"
local SUBJECT_ATTRIBUTE = "Subject"

local function label(instance: Instance)
	if not instance:IsA("ProximityPrompt") then
		return
	end
	local subject = instance:GetAttribute(SUBJECT_ATTRIBUTE)
	if typeof(subject) ~= "string" then
		return
	end
	instance.ObjectText = L.text(`subject.{subject}`)
	instance.ActionText = L.text("class.start")
end

local function labelAll()
	for _, instance in CollectionService:GetTagged(TAG) do
		label(instance)
	end
end

function PromptLabelController.init()
	labelAll()
	CollectionService:GetInstanceAddedSignal(TAG):Connect(label)
	-- A player switching language mid-session should see the doors change too.
	L.Changed:Connect(labelAll)
end

return PromptLabelController
