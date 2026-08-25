--!strict
--- The curated question bank.
---
--- Lives in ServerStorage and is never replicated. It holds the answer keys, so
--- a copy in ReplicatedStorage would be a copy of every answer on every client.
--- Nothing in this module hands a `Question` to a client; LessonService strips
--- the answer before anything crosses the wire.

local ReplicatedStorage = game:GetService("ReplicatedStorage")
local ServerStorage = game:GetService("ServerStorage")

local Subjects = require(ReplicatedStorage.Shared.Config.Subjects)
local Types = require(ReplicatedStorage.Shared.Types)

local BankService = {}

--- Widen the grade window until enough questions are found. A twelve-year-old
--- can answer an eleven-year-old's question; running out of questions entirely
--- is the worse failure.
local MAX_GRADE_WINDOW = 4

local index: { [string]: { [string]: { Types.Question } } } = {}
local byId: { [string]: Types.Question } = {}
local loaded = false

local function ingest(subject: string, locale: string, questions: { any })
	local bySubject = index[subject]
	if bySubject == nil then
		bySubject = {}
		index[subject] = bySubject
	end
	local pool = bySubject[locale]
	if pool == nil then
		pool = {}
		bySubject[locale] = pool
	end

	for _, raw in questions do
		if typeof(raw) ~= "table" or typeof(raw.id) ~= "string" then
			continue
		end
		if byId[raw.id] ~= nil then
			warn(`BankService: duplicate question id "{raw.id}", keeping the first`)
			continue
		end
		local question: Types.Question = {
			id = raw.id,
			-- The subject and locale live on the file, not on each question.
			subject = subject,
			grade = raw.grade,
			stem = raw.stem,
			options = raw.options,
			answer = raw.answer,
			explanation = raw.explanation,
		}
		byId[question.id] = question
		table.insert(pool, question)
	end
end

function BankService.load()
	if loaded then
		return
	end
	loaded = true

	local banks = ServerStorage:FindFirstChild("Banks")
	if banks == nil then
		warn("BankService: ServerStorage.Banks is missing; the school has no questions")
		return
	end

	for _, localeFolder in banks:GetChildren() do
		if not localeFolder:IsA("Folder") then
			continue
		end
		for _, module in localeFolder:GetChildren() do
			if not module:IsA("ModuleScript") then
				continue
			end
			local ok, payload = pcall(require, module)
			if not ok or typeof(payload) ~= "table" then
				warn(`BankService: could not read bank {localeFolder.Name}/{module.Name}`)
				continue
			end
			local file = payload :: any
			if typeof(file.subject) == "string" and typeof(file.questions) == "table" then
				ingest(file.subject, localeFolder.Name, file.questions)
			end
		end
	end
end

function BankService.get(questionId: string): Types.Question?
	return byId[questionId]
end

--- Locale-bound subjects never fall back to another locale. A perfectly
--- translated question about the Russian literature syllabus is still the wrong
--- question for a Spanish student, so serving nothing is better than serving that.
--- Universal subjects may borrow another locale's pool until the translation
--- pipeline exists, because a maths question is a maths question.
local function poolFor(subject: string, locale: string): { Types.Question }
	local bySubject = index[subject]
	if bySubject == nil then
		return {}
	end

	local exact = bySubject[locale]
	if exact ~= nil and #exact > 0 then
		return exact
	end
	if not Subjects.isTranslatable(subject) then
		return {}
	end

	for _, pool in bySubject do
		if #pool > 0 then
			return pool
		end
	end
	return {}
end

local function shuffled<T>(list: { T }, random: Random): { T }
	local copy = table.clone(list)
	for i = #copy, 2, -1 do
		local j = random:NextInteger(1, i)
		copy[i], copy[j] = copy[j], copy[i]
	end
	return copy
end

BankService.shuffled = shuffled

--- Draws `count` questions near `grade`. Returns fewer than asked for only when
--- the pool genuinely cannot supply them.
function BankService.draw(
	subject: string,
	locale: string,
	grade: number,
	count: number,
	random: Random
): { Types.Question }
	local pool = poolFor(subject, locale)
	if #pool == 0 then
		return {}
	end

	for window = 0, MAX_GRADE_WINDOW do
		local eligible: { Types.Question } = {}
		for _, question in pool do
			if math.abs(question.grade - grade) <= window then
				table.insert(eligible, question)
			end
		end
		if #eligible >= count then
			local picked = shuffled(eligible, random)
			while #picked > count do
				table.remove(picked)
			end
			return picked
		end
	end

	local everything = shuffled(pool, random)
	while #everything > count do
		table.remove(everything)
	end
	return everything
end

function BankService.poolSize(subject: string, locale: string): number
	return #poolFor(subject, locale)
end

return BankService
