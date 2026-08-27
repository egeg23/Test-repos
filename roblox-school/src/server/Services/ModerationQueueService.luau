--!strict
--- The queue a dean actually reviews.
---
--- Authored questions are stored per teacher, which is right for reading one but
--- useless for finding them: a dean cannot review a subject they have no way to
--- enumerate. The office existed and the review action existed with nothing in
--- between, so the role was decorative.
---
--- One list per locale and subject, appended on submission and read by whoever
--- holds that office. Entries are references rather than copies -- the question
--- itself stays in the author's book, so a rejection has exactly one place to
--- take effect and the queue can never disagree with it.

local DataStoreService = game:GetService("DataStoreService")

local AuthoringService = require(script.Parent.AuthoringService)

local ModerationQueueService = {}

--- Deep enough that a busy subject is not silently truncated, shallow enough to
--- stay well inside the value size limit.
local MAX_ENTRIES = 200
local CACHE_TTL_SECONDS = 20

local store = DataStoreService:GetDataStore("ModerationQueue_v1")

export type Entry = {
	teacherUserId: number,
	questionId: string,
	submittedAt: number,
}

type CacheEntry = { entries: { Entry }, fetchedAt: number }
local cache: { [string]: CacheEntry } = {}

local function keyFor(locale: string, subject: string): string
	return `{locale}:{subject}`
end

function ModerationQueueService.add(
	locale: string,
	subject: string,
	teacherUserId: number,
	questionId: string
)
	local key = keyFor(locale, subject)
	local ok = pcall(function()
		store:UpdateAsync(key, function(current: any)
			local entries: { Entry } = if typeof(current) == "table"
				then current :: { Entry }
				else {}

			table.insert(entries, {
				teacherUserId = teacherUserId,
				questionId = questionId,
				submittedAt = os.time(),
			})

			-- Oldest out first. A queue that refused new work once full would hide
			-- exactly the submissions nobody has looked at yet.
			while #entries > MAX_ENTRIES do
				table.remove(entries, 1)
			end
			return entries
		end)
	end)

	if ok then
		cache[key] = nil
	end
end

local function read(locale: string, subject: string): { Entry }
	local key = keyFor(locale, subject)
	local cached = cache[key]
	if cached ~= nil and os.clock() - cached.fetchedAt < CACHE_TTL_SECONDS then
		return cached.entries
	end

	local ok, value = pcall(function()
		return store:GetAsync(key)
	end)
	local entries: { Entry } = if ok and typeof(value) == "table"
		then value :: { Entry }
		else {}

	cache[key] = { entries = entries, fetchedAt = os.clock() }
	return entries
end

--- What is still waiting on a decision, with the question attached.
---
--- Entries whose question has since published itself, been rejected, or vanished
--- are dropped from the answer rather than shown as work. The queue is a hint
--- about where to look; the author's book is the truth.
function ModerationQueueService.pending(locale: string, subject: string): { any }
	local results: { any } = {}
	for _, entry in read(locale, subject) do
		local question = AuthoringService.peek(entry.teacherUserId, entry.questionId)
		if question == nil or question.status ~= "pending" then
			continue
		end
		table.insert(results, {
			teacherUserId = entry.teacherUserId,
			questionId = entry.questionId,
			submittedAt = entry.submittedAt,
			publishAt = question.publishAt,
			grade = question.grade,
			stem = question.stem,
			options = question.options,
			answer = question.answer,
			explanation = question.explanation,
		})
	end
	return results
end

--- Removes a reference once it has been decided. Best effort: a leftover entry
--- costs a lookup and is filtered out of `pending` anyway.
function ModerationQueueService.remove(locale: string, subject: string, questionId: string)
	local key = keyFor(locale, subject)
	pcall(function()
		store:UpdateAsync(key, function(current: any)
			if typeof(current) ~= "table" then
				return nil
			end
			local entries = current :: { Entry }
			for index = #entries, 1, -1 do
				if entries[index].questionId == questionId then
					table.remove(entries, index)
				end
			end
			return entries
		end)
	end)
	cache[key] = nil
end

return ModerationQueueService
