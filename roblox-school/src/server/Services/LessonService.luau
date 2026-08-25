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

local function creditTeacher(attempt: Attempt, data: Types.ProfileData, elapsedSeconds: number)
	local key = tostring(attempt.teacherUserId)
	local history = data.teacherHistory[key]
	if history == nil then
		history = { completions = 0, paid = 0 }
		data.teacherHistory[key] = history
	end

	-- Roblox account age, not how long they have played this game: a legitimate
	-- newcomer has a profile created seconds ago, while the thing being screened
	-- out is a freshly registered alt.
	local counts =
		Economy.countsTowardTeacherPayout(attempt.player.AccountAge, data.playSeconds)

	-- The completion is recorded either way. Otherwise a ring could park its
	-- farming on accounts that never age past the gate and reset the decay curve
	-- with every run.
	history.completions += 1
	if not counts then
		return
	end

	local breakdown = Economy.teacherPayout({
		priorCompletions = history.completions - 1,
		lifetimePaidByThisStudent = history.paid,
		actualSeconds = elapsedSeconds,
		expectedSeconds = Economy.ExpectedSecondsPerQuestion * #attempt.questions,
		globalPassRate = LessonStatsService.passRate(attempt.statKey),
		classMembers = attempt.classMembers,
		teacherRating = attempt.teacherRating,
		isTranslatedCompletion = attempt.translated,
	})

	if breakdown.amount <= 0 then
		return
	end
	history.paid += breakdown.amount
	PayoutService.credit(attempt.teacherUserId, breakdown.amount)
end

local function finish(attempt: Attempt)
	attempt.finished = true
	attempts[attempt.player] = nil

	local total = #attempt.questions
	local passed = total > 0 and (attempt.correctCount / total) >= Economy.DefaultPassFraction
	LessonStatsService.record(attempt.statKey, passed)

	local data = DataService.getData(attempt.player)
	if data == nil then
		return
	end

	local hasDoublePass = PurchaseService.ownsPass(attempt.player, "xp2")
	local multiplier = ProgressionService.rewardMultiplier(data, hasDoublePass)
	local points = Economy.studentReward(attempt.correctCount, passed, multiplier)
	data.points += points

	local outcome = ProgressionService.applyLesson(data, attempt.subject, passed, points)

	-- Teaching yourself pays nothing, and a bank lesson has no author to pay.
	if attempt.teacherUserId > 0 and attempt.teacherUserId ~= attempt.player.UserId then
		creditTeacher(attempt, data, os.clock() - attempt.startedAt)
	end

	Remotes.event(Remotes.Names.LessonFinished):FireClient(attempt.player, {
		passed = passed,
		correctCount = attempt.correctCount,
		total = total,
		pointsAwarded = points,
		multiplier = multiplier,
		grade = data.grade,
		advanced = outcome.advanced,
		graduated = outcome.graduated,
	})
end

--- Turns a list of questions into attempt entries, shuffling the options for
--- each one. A leaked answer key that says "the answer is B" is worth nothing
--- once B is somewhere different on every attempt.
local function buildQuestions(drawn: { Types.Question }, random: Random): { AttemptQuestion }
	local questions: { AttemptQuestion } = {}
	for _, question in drawn do
		local order: { number } = {}
		for index = 1, #question.options do
			table.insert(order, index)
		end
		order = BankService.shuffled(order, random)

		local correctPosition = 0
		for position, original in order do
			if original == question.answer then
				correctPosition = position
				break
			end
		end

		table.insert(questions, {
			questionId = question.id,
			order = order,
			correctPosition = correctPosition,
			sentAt = 0,
			chosen = nil,
		})
	end
	return questions
end

type Source = {
	questions: { AttemptQuestion },
	subject: string,
	statKey: string,
	teacherUserId: number,
	classMembers: number,
	teacherRating: number,
	translated: boolean,
}

--- A lesson a teacher assembled, taken inside their class.
local function classSource(
	player: Player,
	data: Types.ProfileData,
	classId: string,
	lessonId: string,
	random: Random
): (Source?, string?)
	local class = ClassService.get(classId)
	if class == nil then
		return nil, "noClass"
	end
	-- Enrolment is what makes the fill rate mean anything, so it is required
	-- rather than implied by knowing the id.
	if data.enrolledClassId ~= classId then
		return nil, "notEnrolled"
	end

	local lesson = class.lessons[lessonId]
	if lesson == nil then
		return nil, "noLesson"
	end
	local test = lesson.test
	if test == nil then
		return nil, "noLesson"
	end

	local candidates: { Types.Question } = {}
	for _, questionId in test.poolIds do
		local question = BankService.get(questionId)
		if question ~= nil then
			table.insert(candidates, question)
		end
	end
	if #candidates == 0 then
		return nil, "noQuestions"
	end

	local picked = BankService.shuffled(candidates, random)
	while #picked > math.max(test.draw, 1) do
		table.remove(picked)
	end

	return {
		questions = buildQuestions(picked, random),
		subject = class.subject,
		-- Quality is measured per lesson here, not per subject: it is this
		-- teacher's test being judged.
		statKey = lessonId,
		teacherUserId = class.teacherUserId,
		classMembers = #class.memberUserIds,
		teacherRating = class.rating,
		translated = class.locale ~= data.locale,
	}, nil
end

--- A lesson drawn straight from the curated bank, run by nobody. This is what
--- keeps the school playable at three in the morning with no teachers online,
--- and what a brand new player meets first.
local function bankSource(
	data: Types.ProfileData,
	subject: string,
	random: Random
): (Source?, string?)
	local drawn =
		BankService.draw(subject, data.locale, data.grade, Economy.QuestionsPerLesson, random)
	if #drawn == 0 then
		return nil, "noQuestions"
	end
	return {
		questions = buildQuestions(drawn, random),
		subject = subject,
		statKey = subject,
		teacherUserId = 0,
		classMembers = 0,
		teacherRating = 0,
		translated = false,
	}, nil
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
