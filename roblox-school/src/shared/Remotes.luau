--!strict
--- Lazily created remote instances, so server and client agree on names without
--- either one depending on a hand-built folder in the place file.

local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local Remotes = {}

local FOLDER_NAME = "Remotes"

Remotes.Names = {
	RequestAd = "RequestAd",
	AdState = "AdState",
	StartLesson = "StartLesson",
	LessonQuestion = "LessonQuestion",
	SubmitAnswer = "SubmitAnswer",
	AnswerResult = "AnswerResult",
	LessonFinished = "LessonFinished",
	LessonRejected = "LessonRejected",
	ClassAction = "ClassAction",
	ClassResult = "ClassResult",
}

local function getFolder(): Folder
	if RunService:IsServer() then
		local existing = ReplicatedStorage:FindFirstChild(FOLDER_NAME)
		if existing ~= nil then
			return existing :: Folder
		end
		local folder = Instance.new("Folder")
		folder.Name = FOLDER_NAME
		folder.Parent = ReplicatedStorage
		return folder
	end
	return ReplicatedStorage:WaitForChild(FOLDER_NAME) :: Folder
end

function Remotes.event(name: string): RemoteEvent
	local folder = getFolder()
	if RunService:IsServer() then
		local existing = folder:FindFirstChild(name)
		if existing ~= nil then
			return existing :: RemoteEvent
		end
		local remote = Instance.new("RemoteEvent")
		remote.Name = name
		remote.Parent = folder
		return remote
	end
	return folder:WaitForChild(name) :: RemoteEvent
end

function Remotes.func(name: string): RemoteFunction
	local folder = getFolder()
	if RunService:IsServer() then
		local existing = folder:FindFirstChild(name)
		if existing ~= nil then
			return existing :: RemoteFunction
		end
		local remote = Instance.new("RemoteFunction")
		remote.Name = name
		remote.Parent = folder
		return remote
	end
	return folder:WaitForChild(name) :: RemoteFunction
end

return Remotes
