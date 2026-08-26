--!strict
--- Resolves a question id, whichever pool it came from.
---
--- A lesson stores ids and nothing else, so this is the single place that decides
--- whether an id is real and whether it may be used. Both callers -- the lesson
--- builder and the class authoring path -- go through here, so an authored
--- question that is still pending is refused everywhere at once rather than in
--- each place that remembered to check.

local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Types = require(ReplicatedStorage.Shared.Types)
local AuthoringService = require(script.Parent.AuthoringService)
local BankService = require(script.Parent.BankService)

local QuestionService = {}

--- Nil for an id that does not exist, is not published yet, or was rejected.
---
--- `locale` picks a translated variant of an authored question where one exists.
--- The curated bank ignores it: bank pools are already chosen per locale before
--- a question id is ever looked up.
function QuestionService.get(questionId: string, locale: string?): Types.Question?
	if AuthoringService.isAuthoredId(questionId) then
		return AuthoringService.resolve(questionId, locale)
	end
	return BankService.get(questionId)
end

--- Whether `player` may put this question into a lesson of their own.
---
--- The bank is common ground. An authored question belongs to whoever wrote it,
--- and stays theirs: without this, a teacher could build a lesson entirely out of
--- someone else's work and be paid for teaching it.
function QuestionService.canUse(questionId: string, userId: number): boolean
	local owner = AuthoringService.parseId(questionId)
	if owner == nil then
		return BankService.get(questionId) ~= nil
	end
	if owner ~= userId then
		return false
	end
	return AuthoringService.resolve(questionId) ~= nil
end

return QuestionService
