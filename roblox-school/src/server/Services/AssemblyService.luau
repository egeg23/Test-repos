--!strict
--- Assembly tasks for science and art.
---
--- A task is a handful of labelled slots and a palette of pieces, some of which
--- are wrong. The student fills the slots; the server marks them. Like the
--- obstacle courses this carries no text a player wrote, so a teacher can build a
--- lesson out of it without waiting on moderation -- but unlike a course, the
--- *answer* comes from the curated catalogue rather than from the teacher. A
--- teacher who could declare which wiring is correct could teach the wrong one,
--- and a child would have no way to tell.
---
--- Tasks live in ServerStorage with the question bank, and for the same reason:
--- the answers are in them.

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local ServerStorage = game:GetService("ServerStorage")

local Components = require(ReplicatedStorage.Shared.Config.Components)
local Economy = require(ReplicatedStorage.Shared.Config.Economy)
local Remotes = require(ReplicatedStorage.Shared.Remotes)
local BankService = require(script.Parent.BankService)
local RateLimiter = require(script.Parent.RateLimiter)
local RewardService = require(script.Parent.RewardService)

local AssemblyService = {}

--- Roughly what one slot is worth in thinking time, used for the engagement
--- factor the same way a question is.
local EXPECTED_SECONDS_PER_SLOT = 20

export type Task = {
	id: string,
	subject: string,
	locale: string,
	grade: number,
	prompt: string,
	slots: { string },
	answers: { string },
	palette: { string },
	explanation: string,
}

type Attempt = {
	player: Player,
	token: string,
	task: Task,
	subject: string,
	statKey: string,
	teacherUserId: number,
	classMembers: number,
	teacherRating: number,
	translated: boolean,
	startedAt: number,
}

export type Source = {
	subject: string,
	statKey: string,
	teacherUserId: number,
	classMembers: number,
	teacherRating: number,
	translated: boolean,
}

local byId: { [string]: Task } = {}
local bySubject: { [string]: { [string]: { Task } } } = {}
local attempts: { [Player]: Attempt } = {}
local loaded = false
local nextToken = 0

local function ingest(subject: string, locale: string, tasks: { any })
	local subjectPools = bySubject[subject]
	if subjectPools == nil then
		subjectPools = {}
		bySubject[subject] = subjectPools
	end
	local pool = subjectPools[locale]
	if pool == nil then
		pool = {}
		subjectPools[locale] = pool
	end

	for _, raw in tasks do
		if typeof(raw) ~= "table" or typeof(raw.id) ~= "string" or byId[raw.id] ~= nil then
			continue
		end
		local task: Task = {
			id = raw.id,
			subject = subject,
			locale = locale,
			grade = raw.grade,
			prompt = raw.prompt,
			slots = raw.slots,
			answers = raw.answers,
			palette = raw.palette,
			explanation = raw.explanation,
		}
		byId[task.id] = task
		table.insert(pool, task)
	end
end

function AssemblyService.load()
	if loaded then
		return
	end
	loaded = true

	local root = ServerStorage:FindFirstChild("Assembly")
	if root == nil then
		warn("AssemblyService: ServerStorage.Assembly is missing; no assembly tasks")
		return
	end

	for _, localeFolder in root:GetChildren() do
		if not localeFolder:IsA("Folder") then
			continue
		end
		for _, module in localeFolder:GetChildren() do
			if not module:IsA("ModuleScript") then
				continue
			end
			local ok, payload = pcall(require, module)
			if ok and typeof(payload) == "table" then
				local file = payload :: any
				if typeof(file.subject) == "string" and typeof(file.tasks) == "table" then
					ingest(file.subject, localeFolder.Name, file.tasks)
				end
			end
		end
	end
end

function AssemblyService.get(taskId: string): Task?
	return byId[taskId]
end

--- Tasks a teacher may pick from, without the answers. The palette is included
--- because it is half of what makes a task good or bad to set.
function AssemblyService.listForAuthoring(subject: string, locale: string, grade: number): { any }
	local pools = bySubject[subject]
	local pool = if pools ~= nil then pools[locale] else nil
	if pool == nil then
		return {}
	end

	local results: { any } = {}
	for _, task in pool do
		if math.abs(task.grade - grade) <= 2 then
			table.insert(results, {
				id = task.id,
				grade = task.grade,
				prompt = task.prompt,
				slotCount = #task.slots,
			})
		end
	end
	return results
end

local function pick(subject: string, locale: string, grade: number, random: Random): Task?
	local pools = bySubject[subject]
	local pool = if pools ~= nil then pools[locale] else nil
	if pool == nil or #pool == 0 then
		return nil
	end

	local eligible: { Task } = {}
	for _, task in pool do
		if math.abs(task.grade - grade) <= 3 then
			table.insert(eligible, task)
		end
	end
	local candidates = if #eligible > 0 then eligible else pool
	return candidates[random:NextInteger(1, #candidates)]
end

local function send(attempt: Attempt, random: Random)
	-- The palette is shuffled per attempt: a fixed order is an answer key that
	-- spreads by word of mouth.
	local palette = BankService.shuffled(attempt.task.palette, random)
	Remotes.event(Remotes.Names.AssemblyTask):FireClient(attempt.player, {
		token = attempt.token,
		prompt = attempt.task.prompt,
		slots = table.clone(attempt.task.slots),
		palette = palette,
	})
end

--- Starts a task. `taskId` picks a specific one; without it a task is drawn from
--- the catalogue for the student's grade.
function AssemblyService.begin(
	player: Player,
	source: Source,
	locale: string,
	grade: number,
	taskId: string?
): string?
	AssemblyService.load()
	if attempts[player] ~= nil then
		return "alreadyAssembling"
	end

	local random = Random.new()
	local task = if taskId ~= nil then byId[taskId] else pick(source.subject, locale, grade, random)
	if task == nil then
		return "noTasks"
	end
	if task.subject ~= source.subject then
		return "wrongSubject"
	end

	nextToken += 1
	local attempt: Attempt = {
		player = player,
		token = `s{nextToken}`,
		task = task,
		subject = source.subject,
		statKey = source.statKey,
		teacherUserId = source.teacherUserId,
		classMembers = source.classMembers,
		teacherRating = source.teacherRating,
		translated = source.translated,
		startedAt = os.clock(),
	}
	attempts[player] = attempt
	send(attempt, random)
	return nil
end

local function onSubmit(player: Player, payload: unknown)
	if not RateLimiter.consume(player, "AssemblySubmit", 4, 0.3) then
		return
	end
	if typeof(payload) ~= "table" then
		return
	end

	local attempt = attempts[player]
	if attempt == nil then
		return
	end
	local request = payload :: any
	if request.token ~= attempt.token then
		return
	end
	if typeof(request.assignments) ~= "table" then
		return
	end

	attempts[player] = nil
	local task = attempt.task
	local correct = 0
	for index, expected in task.answers do
		local given = (request.assignments :: { any })[index]
		-- Only pieces that were actually in the palette count, so a client cannot
		-- invent a component id that happens to match.
		if
			typeof(given) == "string"
			and given == expected
			and Components.get(given) ~= nil
			and table.find(task.palette, given) ~= nil
		then
			correct += 1
		end
	end

	local total = #task.answers
	local passed = total > 0 and (correct / total) >= Economy.DefaultPassFraction

	local summary = RewardService.settle(player, {
		subject = attempt.subject,
		statKey = attempt.statKey,
		passed = passed,
		score = correct,
		total = total,
		teacherUserId = attempt.teacherUserId,
		classMembers = attempt.classMembers,
		teacherRating = attempt.teacherRating,
		translated = attempt.translated,
		elapsedSeconds = os.clock() - attempt.startedAt,
		expectedSeconds = EXPECTED_SECONDS_PER_SLOT * total,
	})

	Remotes.event(Remotes.Names.LessonFinished):FireClient(player, {
		passed = passed,
		correctCount = correct,
		total = total,
		pointsAwarded = if summary ~= nil then summary.pointsAwarded else 0,
		multiplier = if summary ~= nil then summary.multiplier else 1,
		grade = if summary ~= nil then summary.grade else 0,
		advanced = summary ~= nil and summary.advanced or false,
		graduated = summary ~= nil and summary.graduated or false,
		-- Sent whether or not they got it right, as with every other lesson.
		explanation = task.explanation,
		answers = table.clone(task.answers),
	})
end

function AssemblyService.start()
	AssemblyService.load()
	Remotes.event(Remotes.Names.AssemblySubmit).OnServerEvent:Connect(onSubmit)
	Players.PlayerRemoving:Connect(function(player: Player)
		attempts[player] = nil
	end)
end

return AssemblyService
