--!strict
--- The lesson loop: draw questions, ask them one at a time, mark them, pay out.
---
--- Every decision lives on the server. The client receives a stem and a shuffled
--- list of options -- not the answer, not which position holds it, not the
--- questions still to come. Timing is measured from when the server sent a
--- question, never from anything the client reports about itself.

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Economy = require(ReplicatedStorage.Shared.Config.Economy)
local Remotes = require(ReplicatedStorage.Shared.Remotes)
local Subjects = require(ReplicatedStorage.Shared.Config.Subjects)
local Types = require(ReplicatedStorage.Shared.Types)
local BankService = require(script.Parent.BankService)
local DataService = require(script.Parent.DataService)
local PayoutService = require(script.Parent.PayoutService)
local ProgressionService = require(script.Parent.ProgressionService)
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
	})
end

local function finish(attempt: Attempt)
	attempt.finished = true
	attempts[attempt.player] = nil

	local total = #attempt.questions
	local passed = total > 0 and (attempt.correctCount / total) >= Economy.DefaultPassFraction

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
		if class ~= nil and lesson ~= nil and lesson.kind == "obstacle" then
			if data.enrolledClassId ~= request.classId then
				reject(player, "notEnrolled")
				return
			end
			local courseFailure = ObstacleService.begin(player, class, lesson)
			if courseFailure ~= nil then
				reject(player, courseFailure)
			end
			return
		end

		source, failure = classSource(player, data, request.classId, request.lessonId, random)
	elseif typeof(request.subject) == "string" and Subjects.get(request.subject) ~= nil then
		source, failure = bankSource(data, request.subject, random)
	else
		failure = "badRequest"
	end

	if source == nil then
		reject(player, failure or "badRequest")
		return
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
	}

	attempts[player] = attempt
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

function LessonService.start()
	BankService.load()
	LessonStatsService.start()

	Remotes.event(Remotes.Names.StartLesson).OnServerEvent:Connect(onStartLesson)
	Remotes.event(Remotes.Names.SubmitAnswer).OnServerEvent:Connect(onSubmitAnswer)

	Players.PlayerRemoving:Connect(function(player: Player)
		attempts[player] = nil
	end)
end

return LessonService
