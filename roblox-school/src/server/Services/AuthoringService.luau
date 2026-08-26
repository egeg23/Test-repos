--!strict
--- Teacher-written questions.
---
--- This is the half of the hybrid that involves free text, and therefore the half
--- that has to be handled carefully. Roblox restricts free-form user creation to
--- players sixteen and over and bars the experience from ads; the documented way
--- out is content that "undergoes Roblox moderation before publication or
--- replication". So the pipeline is:
---
---   structural rules -> TextService on every field -> pending -> published
---
--- Nothing skips a step, every step fails closed, and a question that has not
--- reached `published` is unreachable by anyone except its author. Not hidden in
--- the interface -- unreachable: `resolve` refuses it, so it cannot be put in a
--- lesson and cannot be sent to a student.
---
--- The hold between filtering and publication exists to give a dean a window to
--- catch what the filter did not. It is defence in depth, not the safeguard: the
--- filter is what the exemption rests on.

local DataStoreService = game:GetService("DataStoreService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Authoring = require(ReplicatedStorage.Shared.Config.Authoring)
local Subjects = require(ReplicatedStorage.Shared.Config.Subjects)
local Types = require(ReplicatedStorage.Shared.Types)
local ModerationService = require(script.Parent.ModerationService)
local TranslationService = require(script.Parent.TranslationService)

local AuthoringService = {}

local HOLD_SECONDS = 10 * 60
local CACHE_TTL_SECONDS = 60

local store = DataStoreService:GetDataStore("AuthoredQuestions_v1")

export type Status = "pending" | "published" | "rejected"

export type Authored = {
	id: string,
	subject: string,
	grade: number,
	locale: string,
	stem: string,
	options: { string },
	answer: number,
	explanation: string,
	status: Status,
	--- Unix seconds after which a pending question publishes itself. A dean can
	--- bring that forward by approving, or stop it by rejecting.
	publishAt: number,
	createdAt: number,
	--- Locale -> the same question in that language, machine-translated and then
	--- filtered again. Only ever populated for universal subjects.
	translations: { [string]: TranslationService.TranslatedQuestion }?,
}

type Book = {
	nextIndex: number,
	questions: { [string]: Authored },
}

type CacheEntry = { book: Book, fetchedAt: number }
local cache: { [number]: CacheEntry } = {}

local function emptyBook(): Book
	return { nextIndex = 1, questions = {} }
end

local function readBook(userId: number, fresh: boolean?): Book
	local entry = cache[userId]
	if not fresh and entry ~= nil and os.clock() - entry.fetchedAt < CACHE_TTL_SECONDS then
		return entry.book
	end

	local ok, value = pcall(function()
		return store:GetAsync(tostring(userId))
	end)
	local book = if ok and typeof(value) == "table" then value :: Book else emptyBook()
	cache[userId] = { book = book, fetchedAt = os.clock() }
	return book
end

--- Ids carry their owner, so a question can be resolved from a lesson without
--- the lesson having to remember whose it was.
local function makeId(userId: number, index: number): string
	return `a:{userId}:{index}`
end

function AuthoringService.parseId(questionId: string): number?
	local owner = string.match(questionId, "^a:(%d+):%d+$")
	return if owner ~= nil then tonumber(owner) else nil
end

function AuthoringService.isAuthoredId(questionId: string): boolean
	return AuthoringService.parseId(questionId) ~= nil
end

local function countLive(book: Book): number
	local count = 0
	for _, question in book.questions do
		if question.status ~= "rejected" then
			count += 1
		end
	end
	return count
end

--- Publishes a pending question whose hold has elapsed. Done lazily on read
--- rather than on a timer: there is no moment at which a question must become
--- available, only a moment before which it must not be.
local function settleStatus(question: Authored): Authored
	if question.status == "pending" and os.time() >= question.publishAt then
		question.status = "published"
	end
	return question
end

--- The only way a question reaches a student. Anything not published returns nil.
---
--- `locale` selects a translated variant when one exists. A missing translation
--- falls back to the original rather than to nothing: a Brazilian student is
--- better served a maths question in Russian than no maths question at all, and
--- the numbers are the same either way.
function AuthoringService.resolve(questionId: string, locale: string?): Types.Question?
	local owner = AuthoringService.parseId(questionId)
	if owner == nil then
		return nil
	end

	local book = readBook(owner)
	local question = book.questions[questionId]
	if question == nil then
		return nil
	end
	settleStatus(question)
	if question.status ~= "published" then
		return nil
	end

	local stem = question.stem
	local options = question.options
	local explanation = question.explanation

	if locale ~= nil and locale ~= question.locale and question.translations ~= nil then
		local variant = question.translations[locale]
		if variant ~= nil then
			stem = variant.stem
			options = variant.options
			explanation = variant.explanation
		end
	end

	return {
		id = question.id,
		subject = question.subject,
		grade = question.grade,
		stem = stem,
		options = table.clone(options),
		-- The answer index is the author's, not the translator's: option order is
		-- preserved through translation, so position 3 stays position 3.
		answer = question.answer,
		explanation = explanation,
	}
end

--- Translates a stored question in the background and writes the result back.
---
--- Deliberately after the store rather than before it. Submission would otherwise
--- block on a dozen network calls, and the hold before publication is far longer
--- than this takes -- so translations are ready well before anyone can see the
--- question, and a translation failure simply means it publishes in one language.
local function translateInBackground(userId: number, questionId: string, draft: Authoring.Draft, locale: string)
	task.spawn(function()
		local translations = TranslationService.translateQuestion(
			draft.subject,
			locale,
			userId,
			draft.stem,
			draft.options,
			draft.explanation
		)
		if next(translations) == nil then
			return
		end

		local ok = pcall(function()
			store:UpdateAsync(tostring(userId), function(current: any)
				if typeof(current) ~= "table" then
					return nil
				end
				local book = current :: Book
				local question = book.questions[questionId]
				if question == nil then
					return nil
				end
				question.translations = translations
				return book
			end)
		end)
		if ok then
			cache[userId] = nil
		end
	end)
end

--- Filters every field. Returns nil if any one of them could not be cleared,
--- because a question with one unfiltered option is an unfiltered question.
local function filterDraft(draft: Authoring.Draft, authorUserId: number): Authoring.Draft?
	local stem = ModerationService.filterForBroadcast(draft.stem, authorUserId)
	if stem == nil then
		return nil
	end
	local explanation = ModerationService.filterForBroadcast(draft.explanation, authorUserId)
	if explanation == nil then
		return nil
	end

	local options: { string } = {}
	for _, option in draft.options do
		local filtered = ModerationService.filterForBroadcast(option, authorUserId)
		if filtered == nil then
			return nil
		end
		table.insert(options, filtered)
	end

	return {
		subject = draft.subject,
		grade = draft.grade,
		stem = stem,
		options = options,
		answer = draft.answer,
		explanation = explanation,
	}
end

local function coerceDraft(payload: any): Authoring.Draft?
	if typeof(payload) ~= "table" then
		return nil
	end
	if
		typeof(payload.subject) ~= "string"
		or typeof(payload.grade) ~= "number"
		or typeof(payload.stem) ~= "string"
		or typeof(payload.explanation) ~= "string"
		or typeof(payload.answer) ~= "number"
		or typeof(payload.options) ~= "table"
	then
		return nil
	end

	local options: { string } = {}
	for _, option in payload.options :: { any } do
		if typeof(option) ~= "string" then
			return nil
		end
		table.insert(options, option)
	end

	return {
		subject = payload.subject,
		grade = math.floor(payload.grade),
		stem = payload.stem,
		options = options,
		answer = math.floor(payload.answer),
		explanation = payload.explanation,
	}
end

function AuthoringService.submit(
	player: Player,
	locale: string,
	payload: any
): (string?, string?)
	local draft = coerceDraft(payload)
	if draft == nil then
		return nil, "badRequest"
	end
	if Subjects.get(draft.subject) == nil then
		return nil, "unknownSubject"
	end

	-- Structural rules first: they are free, and there is no reason to spend six
	-- filter calls on a draft with three options.
	local structural = Authoring.validate(draft)
	if not structural.ok then
		return nil, structural.reason
	end

	local book = readBook(player.UserId, true)
	if countLive(book) >= Authoring.MaxAuthoredPerTeacher then
		return nil, "authoredLimit"
	end

	local filtered = filterDraft(draft, player.UserId)
	if filtered == nil then
		return nil, "textRejected"
	end
	-- Filtering can lengthen a field (words become hashes of equal length, but
	-- the structural check ran on the original), so the rules are applied again
	-- to what will actually be stored.
	local afterFilter = Authoring.validate(filtered)
	if not afterFilter.ok then
		return nil, afterFilter.reason
	end

	local questionId = ""
	local ok = pcall(function()
		store:UpdateAsync(tostring(player.UserId), function(current: any)
			local live: Book = if typeof(current) == "table" then current :: Book else emptyBook()
			if countLive(live) >= Authoring.MaxAuthoredPerTeacher then
				return nil
			end

			local index = live.nextIndex
			questionId = makeId(player.UserId, index)
			live.nextIndex = index + 1
			live.questions[questionId] = {
				id = questionId,
				subject = filtered.subject,
				grade = filtered.grade,
				locale = locale,
				stem = filtered.stem,
				options = filtered.options,
				answer = filtered.answer,
				explanation = filtered.explanation,
				status = "pending",
				publishAt = os.time() + HOLD_SECONDS,
				createdAt = os.time(),
				translations = nil,
			}
			return live
		end)
	end)

	if not ok or questionId == "" then
		return nil, "storeFailed"
	end
	cache[player.UserId] = nil
	translateInBackground(player.UserId, questionId, filtered, locale)
	return questionId, nil
end

--- The author's own view. Includes pending and rejected questions, because they
--- are the one person entitled to see their own drafts.
function AuthoringService.listMine(player: Player): { any }
	local book = readBook(player.UserId, true)
	local results: { any } = {}
	for _, question in book.questions do
		settleStatus(question)
		table.insert(results, {
			id = question.id,
			subject = question.subject,
			grade = question.grade,
			stem = question.stem,
			options = table.clone(question.options),
			answer = question.answer,
			explanation = question.explanation,
			status = question.status,
			publishAt = question.publishAt,
		})
	end
	return results
end

--- A dean's verdict: approve brings publication forward, reject stops it for good.
---
--- `subject` is the one the caller holds office in, and it is checked against the
--- question rather than trusted. The caller can only establish that the player is
--- a dean of the subject they named -- naming their own subject while pointing at
--- a question from another is exactly the gap that leaves.
function AuthoringService.review(
	teacherUserId: number,
	questionId: string,
	subject: string,
	approve: boolean
): boolean
	local applied = false
	local ok = pcall(function()
		store:UpdateAsync(tostring(teacherUserId), function(current: any)
			if typeof(current) ~= "table" then
				return nil
			end
			local book = current :: Book
			local question = book.questions[questionId]
			if question == nil or question.subject ~= subject then
				return nil
			end
			question.status = if approve then "published" else "rejected"
			if approve then
				question.publishAt = os.time()
			end
			applied = true
			return book
		end)
	end)

	if ok and applied then
		cache[teacherUserId] = nil
	end
	return ok and applied
end

return AuthoringService
