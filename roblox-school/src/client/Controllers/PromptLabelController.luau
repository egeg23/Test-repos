--!strict
--- Labels the world in the player's own language: the classroom prompts, and
--- every sign on every wall.
---
--- Done on the client because the world is a replicated instance tree. A prompt's
--- text, or a sign's, is one value shared by everyone on the server, so writing a
--- language into it from the server picks that language for the whole room.
--- Property changes made on a client stay on that client, which is exactly what
--- is wanted here.
---
--- The server writes the English fallback and tags what it wrote, so a sign is
--- never blank -- it is either the player's language or a real word in another
--- one, and never an empty plate or a raw key.

local CollectionService = game:GetService("CollectionService")

local L = require(script.Parent.Parent.Locale)

local PromptLabelController = {}

local PROMPT_TAG = "SubjectPrompt"
local SUBJECT_ATTRIBUTE = "Subject"
local SIGN_TAG = "WorldSign"
local SIGN_KEY_ATTRIBUTE = "StringKey"

local function labelPrompt(instance: Instance)
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

local function labelSign(instance: Instance)
	if not instance:IsA("TextLabel") then
		return
	end
	local key = instance:GetAttribute(SIGN_KEY_ATTRIBUTE)
	if typeof(key) ~= "string" then
		return
	end
	instance.Text = L.text(key)
end

local function labelAll()
	for _, instance in CollectionService:GetTagged(PROMPT_TAG) do
		labelPrompt(instance)
	end
	for _, instance in CollectionService:GetTagged(SIGN_TAG) do
		labelSign(instance)
	end
end

function PromptLabelController.init()
	labelAll()
	-- Signs stream in as the player walks the corridor rather than all existing
	-- at join, so new ones have to be caught as they arrive, not only once.
	CollectionService:GetInstanceAddedSignal(PROMPT_TAG):Connect(labelPrompt)
	CollectionService:GetInstanceAddedSignal(SIGN_TAG):Connect(labelSign)
	-- A player switching language mid-session should see the doors change too.
	L.Changed:Connect(labelAll)
end

return PromptLabelController
