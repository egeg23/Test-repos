--!strict
--- The lesson loop: draw questions, ask them one at a time, mark them, pay out.
---
--- Every decision lives on the server. The client receives a stem and a shuffled
--- list of options -- not the answer, not which position holds it, not the
--- questions still to come. Timing is measured from when the server sent a
--- question, never from anything the client reports about itself.

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Limits = require(ReplicatedStorage.Shared.Config.Limits)
local Economy = require(ReplicatedStorage.Shared.Config.Economy)
local Remotes = require(ReplicatedStorage.Shared.Remotes)
local Subjects = require(ReplicatedStorage.Shared.Config.Subjects)
local BankService = require(script.Parent.BankService)
local DataService = require(script.Parent.DataService)
local ClassService = require(script.Parent.ClassService)
local LessonStatsService = require(script.Parent.LessonStatsService)
local PurchaseService = require(script.Parent.PurchaseService)
local RateLimiter = require(script.Parent.RateLimiter)

local LessonService = {}

type AttemptQuestion = {
	questionId: string,
	--- order[position] is the index of the original option shown at that position.
	order: { number },
	correctPosition: number,
	sentAt: number,
	chosen: number?,
}

type Attempt = {
	player: Player,
	--- Guards against a client replaying answers from an abandoned attempt.
	token: string,
	subject: string,
	statKey: string,
	teacherUserId: number,
	classMembers: number,
	teacherRating: number,
	translated: boolean,
	questions: { AttemptQuestion },
	position: number,
	correctCount: number,
	startedAt: number,
	finished: boolean,
	--- Hints spent this attempt, and the options already removed per question.
	--- Per question rather than per attempt so two hints on one question cannot
	--- strip it down to a single choice.
	hintsUsed: number,
	hintedOptions: { [number]: { number } },
}

local attempts: { [Player]: Attempt } = {}

local nextToken = 0

local function issueToken(): string
	nextToken += 1
	return `a{nextToken}`
end

local function reject(player: Player, reason: string)
	Remotes.event(Remotes.Names.LessonRejected):FireClient(player, reason)
end

local function sendQuestion(attempt: Attempt)
	local entry = attempt.questions[attempt.position]
	local question = BankService.get(entry.questionId)
	if question == nil then
		return
	end

	local options: { string } = {}
	for _, original in entry.order do
		table.insert(options, question.options[original])
	end

	entry.sentAt = os.clock()
	Remotes.event(Remotes.Names.LessonQuestion):FireClient(attempt.player, {
		token = attempt.token,
		position = attempt.position,
		total = #attempt.questions,
		stem = question.stem,
		options = options,
		removed = attempt.hintedOptions[attempt.position],
		hintsLeft = Limits.HintsPerLesson - attempt.hintsUsed,
	})
end

--- Removes a wrong option from the question in front of the student.
---
--- The server picks which one and remembers it. A client that chose would be a
--- client that could ask for the correct one to be "removed" and read the answer
--- out of the refusal; a server that forgot would let the same hint be spent
--- twice on one question and leave a single choice standing.
local function useHint(player: Player)
	local attempt = attempts[player]
	if attempt == nil or attempt.finished then
		return
	end
	if attempt.hintsUsed >= Limits.HintsPerLesson then
		reject(player, "noHintsLeft")
		return
	end
	if not PurchaseService.ownsPass(player, "hint") then
		reject(player, "needsHintPass")
		return
	end

	local entry = attempt.questions[attempt.position]
	if entry == nil then
		return
	end

	local already = attempt.hintedOptions[attempt.position] or {}
	local candidates: { number } = {}
	for position = 1, #entry.order do
		if position == entry.correctPosition then
			continue
		end
		if table.find(already, position) == nil then
			table.insert(candidates, position)
		end
	end
	-- Never strip a question below two standing options: past that a hint is not
	-- help, it is the answer.
	if #candidates == 0 or #entry.order - #already <= 2 then
		reject(player, "noHintsLeft")
		return
	end

	local chosen = candidates[Random.new():NextInteger(1, #candidates)]
	table.insert(already, chosen)
	attempt.hintedOptions[attempt.position] = already
	attempt.hintsUsed += 1

	Remotes.event(Remotes.Names.LessonHint):FireClient(player, {
		token = attempt.token,
		position = attempt.position,
		removed = already,
		hintsLeft = Limits.HintsPerLesson - attempt.hintsUsed,
	})
end

local function finish(attempt: Attempt)
	attempt.finished = true
	attempts[attempt.player] = nil

	local total = #attempt.questions
	local passed = total > 0 and (attempt.correctCount / total) >= Economy.DefaultPassFraction

	-- Failing closes this lesson to this student for a few minutes. Per lesson,
	-- not per player, so failing maths does not stop them doing history -- and
	-- retrying one lesson twenty times in a row is both how a question pool gets
	-- brute-forced and the cheapest way to farm the teacher who wrote it.
	local data = DataService.getData(attempt.player)
	if data ~= nil and not passed then
		data.retryCooldowns[attempt.statKey] = os.time()
	end

	local summary = RewardService.settle(attempt.player, {
		subject = attempt.subject,
		statKey = attempt.statKey,
		passed = passed,
		score = attempt.correctCount,
		total = total,
		teacherUserId = attempt.teacherUserId,
		classMembers = attempt.classMembers,
		teacherRating = attempt.teacherRating,
		translated = attempt.translated,
		elapsedSeconds = os.clock() - attempt.startedAt,
		expectedSeconds = Economy.ExpectedSecondsPerQuestion * total,
	})
	if summary == nil then
		return
	end

	Remotes.event(Remotes.Names.LessonFinished):FireClient(attempt.player, {
		passed = summary.passed,
		correctCount = summary.score,
		total = summary.total,
		pointsAwarded = summary.pointsAwarded,
		multiplier = summary.multiplier,
		grade = summary.grade,
		advanced = summary.advanced,
		graduated = summary.graduated,
	})
end

local function onStartLesson(player: Player, payload: unknown)
	-- Three in reserve, then roughly one per seven seconds. Abandoning an attempt
	-- costs nothing, so without this a client could reroll until it drew an easy
	-- set of questions.
	if not RateLimiter.consume(player, "StartLesson", 3, 0.15) then
		return
	end
	if typeof(payload) ~= "table" then
		return
	end

	local request = payload :: any
	local data = DataService.getData(player)
	if data == nil then
		reject(player, "notLoaded")
		return
	end
	if data.awaitingGraduation then
		reject(player, "awaitingGraduation")
		return
	end

	local random = Random.new()
	local source: Source?
	local failure: string?

	if typeof(request.classId) == "string" and typeof(request.lessonId) == "string" then
		-- PE is not a quiz. A course has its own lifecycle -- geometry, physics,
		-- checkpoints -- so it is handed off whole rather than squeezed through
		-- the question loop.
		local class = ClassService.get(request.classId)
		local lesson = if class ~= nil then class.lessons[request.lessonId] else nil
		if class ~= nil and lesson ~= nil and lesson.kind ~= "quiz" then
			if data.enrolledClassId ~= request.classId then
				reject(player, "notEnrolled")
				return
			end
			-- Whatever quiz was open is over. Leaving it live would let a student
			-- run a course and answer questions at the same time, and would keep
			-- an attempt around with no way to reach it.
			attempts[player] = nil

			if lesson.kind == "obstacle" then
				local courseFailure = ObstacleService.begin(player, class, lesson)
				if courseFailure ~= nil then
					reject(player, courseFailure)
				end
				return
			end

			local spec = lesson.assembly
			if lesson.kind == "assembly" and spec ~= nil and #spec.taskIds > 0 then
				local taskId = spec.taskIds[Random.new():NextInteger(1, #spec.taskIds)]
				local refusal = AssemblyService.begin(player, {
					subject = class.subject,
					statKey = lesson.id,
					teacherUserId = class.teacherUserId,
					classMembers = ClassService.liveMembers(class),
					teacherRating = class.rating,
					translated = class.locale ~= data.locale,
				}, data.locale, data.grade, taskId)
				if refusal ~= nil then
					reject(player, refusal)
				end
				return
			end

			reject(player, "noLesson")
			return
		end

		source, failure = classSource(player, data, request.classId, request.lessonId, random)
	elseif typeof(request.subject) == "string" and Subjects.get(request.subject) ~= nil then
		-- Science and art can be asked for as an assembly instead of a quiz.
		if request.kind == "assembly" and Subjects.allows(request.subject, "assembly") then
			attempts[player] = nil
			local assemblyFailure = AssemblyService.begin(player, {
				subject = request.subject,
				statKey = `{request.subject}:assembly`,
				teacherUserId = 0,
				classMembers = 0,
				teacherRating = 0,
				translated = false,
			}, data.locale, data.grade, nil)
			if assemblyFailure ~= nil then
				reject(player, assemblyFailure)
			end
			return
		end
		source, failure = bankSource(data, request.subject, random)
	else
		failure = "badRequest"
	end

	if source == nil then
		reject(player, failure or "badRequest")
		return
	end

	-- A lesson failed a few minutes ago is closed, unless the student spends a
	-- charge to reopen it. The charge is spent here rather than on the shop
	-- button, so buying one and never using it leaves it in the profile.
	local remaining = Limits.retryRemaining(data.retryCooldowns[source.statKey] or 0, os.time())
	if remaining > 0 then
		local spare: number = data.consumables.attempt or 0
		if spare <= 0 then
			reject(player, "onCooldown")
			return
		end
		data.consumables.attempt = spare - 1
		data.retryCooldowns[source.statKey] = nil
	end

	local attempt: Attempt = {
		player = player,
		token = issueToken(),
		subject = source.subject,
		statKey = source.statKey,
		teacherUserId = source.teacherUserId,
		classMembers = source.classMembers,
		teacherRating = source.teacherRating,
		translated = source.translated,
		questions = source.questions,
		position = 1,
		correctCount = 0,
		startedAt = os.clock(),
		finished = false,
		hintsUsed = 0,
		hintedOptions = {},
	}

	attempts[player] = attempt
	Analytics.lessonStarted(player, source.subject, "quiz")
	sendQuestion(attempt)
end

local function onSubmitAnswer(player: Player, payload: unknown)
	if not RateLimiter.consume(player, "SubmitAnswer", 10, 2) then
		return
	end
	if typeof(payload) ~= "table" then
		return
	end

	local attempt = attempts[player]
	if attempt == nil or attempt.finished then
		return
	end

	local request = payload :: any
	-- Position must match exactly: this is what stops a client answering ahead,
	-- or replaying a correct answer for a question it has already seen.
	if request.token ~= attempt.token or request.position ~= attempt.position then
		return
	end

	local entry = attempt.questions[attempt.position]
	if entry == nil or entry.chosen ~= nil then
		return
	end

	local choice = request.choice
	if typeof(choice) ~= "number" then
		return
	end
	local picked = math.floor(choice)
	if picked < 1 or picked > #entry.order then
		return
	end

	entry.chosen = picked
	local correct = picked == entry.correctPosition
	if correct then
		attempt.correctCount += 1
	end

	local question = BankService.get(entry.questionId)
	Remotes.event(Remotes.Names.AnswerResult):FireClient(player, {
		position = attempt.position,
		correct = correct,
		correctPosition = entry.correctPosition,
		-- The explanation is the point of the whole exercise, so it is sent
		-- whether the player got it right or wrong.
		explanation = if question ~= nil then question.explanation else "",
	})

	attempt.position += 1
	if attempt.position > #attempt.questions then
		finish(attempt)
	else
		sendQuestion(attempt)
	end
end

--- Starts a bank lesson without a client request. Used by the world's NPC
--- teachers, where the proximity prompt the server itself heard is the whole
--- authorisation -- passing it back through a remote would only add a step a
--- client could lie in.
function LessonService.startFromWorld(player: Player, subject: string, kind: string?)
	onStartLesson(player, { subject = subject, kind = kind })
end

function LessonService.start()
	BankService.load()
	LessonStatsService.start()

	Remotes.event(Remotes.Names.StartLesson).OnServerEvent:Connect(onStartLesson)
	Remotes.event(Remotes.Names.SubmitAnswer).OnServerEvent:Connect(onSubmitAnswer)
	Remotes.event(Remotes.Names.UseHint).OnServerEvent:Connect(function(player: Player)
		-- Metered: a hint is a cheap call but it reads a pass, which is a web
		-- request when the ownership cache is cold.
		if RateLimiter.consume(player, "UseHint", 3, 0.3) then
			useHint(player)
		end
	end)

	Players.PlayerRemoving:Connect(function(player: Player)
		attempts[player] = nil
	end)
end

return LessonService
