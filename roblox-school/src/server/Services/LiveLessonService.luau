--!strict
--- Live lessons: a teacher running a class in real time.
---
--- The asynchronous lesson is the skeleton -- it is what keeps the school
--- working at three in the morning. This is the version worth turning up for: the
--- teacher pushes each question when the class is ready, everyone answers at
--- once, and both sides earn more for having been there.
---
--- Scope worth stating plainly: a session lives on one server. Participants have
--- to be in the same place at the same time, which is what "live" means here.
--- Spanning servers would need MessagingService and a different design; the
--- matchmaking signals exist partly so classmates land together in the first
--- place.
---
--- Option order is shuffled per participant, not per session. In a room full of
--- children answering the same question at the same moment, one shared "it's B"
--- would otherwise settle it for everyone.

local HttpService = game:GetService("HttpService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Economy = require(ReplicatedStorage.Shared.Config.Economy)
local Remotes = require(ReplicatedStorage.Shared.Remotes)
local Types = require(ReplicatedStorage.Shared.Types)
local BankService = require(script.Parent.BankService)
local ClassService = require(script.Parent.ClassService)
local DataService = require(script.Parent.DataService)
local QuestionService = require(script.Parent.QuestionService)
local RateLimiter = require(script.Parent.RateLimiter)
local RewardService = require(script.Parent.RewardService)

local LiveLessonService = {}

local MAX_QUESTIONS = 10

type Participant = {
	player: Player,
	--- Permutation of the current question's options for this participant.
	order: { number },
	correctPosition: number,
	answered: boolean,
	correctCount: number,
}

type Session = {
	id: string,
	teacher: Player,
	classId: string,
	subject: string,
	statKey: string,
	classMembers: number,
	teacherRating: number,
	questions: { Types.Question },
	index: number,
	participants: { [Player]: Participant },
	startedAt: number,
	finished: boolean,
}

local sessions: { [string]: Session } = {}
local sessionOf: { [Player]: string } = {}

local function tell(player: Player, payload: { [string]: any })
	Remotes.event(Remotes.Names.LiveState):FireClient(player, payload)
end

local function broadcast(session: Session, payload: { [string]: any })
	tell(session.teacher, payload)
	for player in session.participants do
		tell(player, payload)
	end
end

local function currentQuestion(session: Session): Types.Question?
	return session.questions[session.index]
end

--- Deals the current question to one participant with its own option order.
local function deal(session: Session, participant: Participant, random: Random)
	local question = currentQuestion(session)
	if question == nil then
		return
	end

	local order: { number } = {}
	for index = 1, #question.options do
		table.insert(order, index)
	end
	order = BankService.shuffled(order, random)

	local correctPosition = 0
	local options: { string } = {}
	for position, original in order do
		table.insert(options, question.options[original])
		if original == question.answer then
			correctPosition = position
		end
	end

	participant.order = order
	participant.correctPosition = correctPosition
	participant.answered = false

	tell(participant.player, {
		event = "question",
		sessionId = session.id,
		position = session.index,
		total = #session.questions,
		stem = question.stem,
		options = options,
	})
end

local function answeredCount(session: Session): (number, number)
	local answered, total = 0, 0
	for _, participant in session.participants do
		total += 1
		if participant.answered then
			answered += 1
		end
	end
	return answered, total
end

local function tellTeacherProgress(session: Session)
	local answered, total = answeredCount(session)
	tell(session.teacher, {
		event = "progress",
		sessionId = session.id,
		position = session.index,
		total = #session.questions,
		answered = answered,
		participants = total,
	})
end

local function settle(session: Session)
	session.finished = true
	local total = #session.questions

	-- Snapshotted first. Settling yields, and a player leaving during one of
	-- those yields removes their key from `participants` -- mutating a table
	-- while a generic for is walking it, which Lua does not define.
	local roll: { Participant } = {}
	for _, participant in session.participants do
		table.insert(roll, participant)
	end

	for _, participant in roll do
		local player = participant.player
		sessionOf[player] = nil
		local passed = total > 0
			and (participant.correctCount / total) >= Economy.DefaultPassFraction

		local summary = RewardService.settle(player, {
			subject = session.subject,
			statKey = session.statKey,
			passed = passed,
			score = participant.correctCount,
			total = total,
			teacherUserId = session.teacher.UserId,
			classMembers = session.classMembers,
			teacherRating = session.teacherRating,
			translated = false,
			elapsedSeconds = os.clock() - session.startedAt,
			expectedSeconds = Economy.ExpectedSecondsPerQuestion * total,
		})

		-- Paid on top of what the settlement already granted, so the live bonus
		-- stacks with passes, ad boosts and whatever the director is running.
		local bonus = 0
		if summary ~= nil then
			bonus = math.floor(summary.pointsAwarded * (Economy.LiveLessonMultiplier - 1))
			local data = DataService.getData(player)
			if data ~= nil and bonus > 0 then
				data.points += bonus
			end
		end

		tell(player, {
			event = "finished",
			sessionId = session.id,
			passed = passed,
			correctCount = participant.correctCount,
			total = total,
			pointsAwarded = (if summary ~= nil then summary.pointsAwarded else 0) + bonus,
			liveBonus = bonus,
		})
	end

	sessionOf[session.teacher] = nil
	tell(session.teacher, {
		event = "ended",
		sessionId = session.id,
		participants = 0,
	})
	sessions[session.id] = nil
end

local function advance(session: Session)
	if session.finished then
		return
	end
	session.index += 1
	if session.index > #session.questions then
		settle(session)
		return
	end

	local random = Random.new()
	for _, participant in session.participants do
		deal(session, participant, random)
	end
	tellTeacherProgress(session)
end

--- Reveals the answer to everyone, then moves on. Kept as one step because a
--- teacher clicking "next" while a child is still reading the explanation is the
--- normal failure of a live class, and the explanation is the whole point.
local function reveal(session: Session)
	local question = currentQuestion(session)
	if question == nil then
		return
	end
	for _, participant in session.participants do
		tell(participant.player, {
			event = "reveal",
			sessionId = session.id,
			position = session.index,
			correctPosition = participant.correctPosition,
			explanation = question.explanation,
		})
	end
	tell(session.teacher, {
		event = "revealed",
		sessionId = session.id,
		position = session.index,
		explanation = question.explanation,
	})
end

local function endSession(session: Session, reason: string)
	if session.finished then
		return
	end
	session.finished = true
	for player in session.participants do
		sessionOf[player] = nil
		tell(player, { event = "ended", sessionId = session.id, reason = reason })
	end
	sessionOf[session.teacher] = nil
	tell(session.teacher, { event = "ended", sessionId = session.id, reason = reason })
	sessions[session.id] = nil
end

local function open(teacher: Player, classId: unknown, lessonId: unknown): (boolean, string?)
	if typeof(classId) ~= "string" or typeof(lessonId) ~= "string" then
		return false, "badRequest"
	end
	if sessionOf[teacher] ~= nil then
		return false, "alreadyLive"
	end

	local data = DataService.getData(teacher)
	if data == nil then
		return false, "notLoaded"
	end

	local class = ClassService.get(classId :: string, true)
	if class == nil or class.teacherUserId ~= teacher.UserId then
		return false, "notOwner"
	end
	local lesson = class.lessons[lessonId :: string]
	if lesson == nil or lesson.kind ~= "quiz" or lesson.test == nil then
		return false, "notALiveLesson"
	end

	local questions: { Types.Question } = {}
	for _, questionId in lesson.test.poolIds do
		local question = QuestionService.get(questionId, class.locale)
		if question ~= nil then
			table.insert(questions, question)
		end
		if #questions >= MAX_QUESTIONS then
			break
		end
	end
	if #questions == 0 then
		return false, "noQuestions"
	end

	local session: Session = {
		id = HttpService:GenerateGUID(false),
		teacher = teacher,
		classId = classId :: string,
		subject = class.subject,
		statKey = lesson.id,
		classMembers = ClassService.liveMembers(class),
		teacherRating = class.rating,
		questions = questions,
		index = 0,
		participants = {},
		startedAt = os.clock(),
		finished = false,
	}
	sessions[session.id] = session
	sessionOf[teacher] = session.id

	-- Only students of this class, only the ones already here. A live lesson is
	-- an invitation to a room, not a notification.
	for _, player in Players:GetPlayers() do
		if player == teacher then
			continue
		end
		local playerData = DataService.getData(player)
		if playerData ~= nil and playerData.enrolledClassId == session.classId then
			tell(player, {
				event = "invite",
				sessionId = session.id,
				title = lesson.title,
				teacherName = teacher.DisplayName,
				total = #questions,
			})
		end
	end

	tell(teacher, {
		event = "opened",
		sessionId = session.id,
		title = lesson.title,
		total = #questions,
	})
	return true, nil
end

local function join(player: Player, sessionId: unknown): (boolean, string?)
	if typeof(sessionId) ~= "string" then
		return false, "badRequest"
	end
	local session = sessions[sessionId :: string]
	if session == nil or session.finished then
		return false, "noSession"
	end
	if sessionOf[player] ~= nil then
		return false, "alreadyInLesson"
	end

	local data = DataService.getData(player)
	if data == nil or data.enrolledClassId ~= session.classId then
		return false, "notEnrolled"
	end

	local participant: Participant = {
		player = player,
		order = {},
		correctPosition = 0,
		answered = false,
		correctCount = 0,
	}
	session.participants[player] = participant
	sessionOf[player] = session.id

	-- Joining after the lesson has started drops the newcomer straight into the
	-- current question rather than making them wait for the next one.
	if session.index >= 1 then
		deal(session, participant, Random.new())
	else
		tell(player, {
			event = "waiting",
			sessionId = session.id,
			total = #session.questions,
		})
	end
	tellTeacherProgress(session)
	return true, nil
end

local function answer(player: Player, choice: unknown): boolean
	local sessionId = sessionOf[player]
	if sessionId == nil then
		return false
	end
	local session = sessions[sessionId]
	if session == nil or session.finished or session.index < 1 then
		return false
	end
	local participant = session.participants[player]
	if participant == nil or participant.answered then
		return false
	end
	if typeof(choice) ~= "number" then
		return false
	end

	local picked = math.floor(choice :: number)
	if picked < 1 or picked > #participant.order then
		return false
	end

	participant.answered = true
	if picked == participant.correctPosition then
		participant.correctCount += 1
	end
	-- No reveal here. In a live lesson the teacher decides when the answer is
	-- shown, which is the difference between a class and a quiz.
	tell(player, { event = "received", sessionId = session.id, position = session.index })
	tellTeacherProgress(session)
	return true
end

local function onAction(player: Player, payload: unknown)
	if typeof(payload) ~= "table" then
		return
	end
	local message = payload :: any
	local action = message.action
	if typeof(action) ~= "string" then
		return
	end
	if not RateLimiter.consume(player, `Live:{action}`, 6, 1) then
		return
	end

	if action == "open" then
		local ok, reason = open(player, message.classId, message.lessonId)
		if not ok then
			tell(player, { event = "rejected", reason = reason })
		end
		return
	end
	if action == "join" then
		local ok, reason = join(player, message.sessionId)
		if not ok then
			tell(player, { event = "rejected", reason = reason })
		end
		return
	end
	if action == "answer" then
		answer(player, message.choice)
		return
	end

	-- The rest are the teacher's controls.
	local sessionId = sessionOf[player]
	if sessionId == nil then
		return
	end
	local session = sessions[sessionId]
	if session == nil or session.teacher ~= player then
		return
	end

	if action == "next" then
		advance(session)
	elseif action == "reveal" then
		reveal(session)
	elseif action == "end" then
		endSession(session, "teacherEnded")
	end
end

function LiveLessonService.start()
	Remotes.event(Remotes.Names.LiveAction).OnServerEvent:Connect(onAction)

	Players.PlayerRemoving:Connect(function(player: Player)
		local sessionId = sessionOf[player]
		if sessionId == nil then
			return
		end
		local session = sessions[sessionId]
		sessionOf[player] = nil
		if session == nil then
			return
		end

		if session.teacher == player then
			-- Without the teacher there is no lesson. Ending it is honest; leaving
			-- a room of children staring at a frozen question is not.
			endSession(session, "teacherLeft")
		else
			session.participants[player] = nil
			tellTeacherProgress(session)
		end
	end)
end

return LiveLessonService
