--!strict
--- Classes: creating them, joining them, ranking them, and the lessons in them.
---
--- A class is persistent (DataStore) because it has to outlive the server the
--- teacher happened to be on, and browsable (MemoryStore sorted map) because
--- listing is impossible over a DataStore. The two are kept in step by
--- republishing a summary after every mutation.
---
--- Directory entries carry a three-day TTL and are refreshed on activity, so a
--- class nobody has touched in three days quietly stops being surfaced. That is
--- the intended behaviour rather than a limitation: a dead class at the top of
--- the list is worse than no class.

local DataStoreService = game:GetService("DataStoreService")
local HttpService = game:GetService("HttpService")
local MemoryStoreService = game:GetService("MemoryStoreService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Economy = require(ReplicatedStorage.Shared.Config.Economy)
local Obstacles = require(ReplicatedStorage.Shared.Config.Obstacles)
local Subjects = require(ReplicatedStorage.Shared.Config.Subjects)
local Types = require(ReplicatedStorage.Shared.Types)
local Remotes = require(ReplicatedStorage.Shared.Remotes)
local AssemblyService = require(script.Parent.AssemblyService)
local AuthoringService = require(script.Parent.AuthoringService)
local BankService = require(script.Parent.BankService)
local CampusService = require(script.Parent.CampusService)
local DataService = require(script.Parent.DataService)
local ModerationService = require(script.Parent.ModerationService)
local PayoutService = require(script.Parent.PayoutService)
local PurchaseService = require(script.Parent.PurchaseService)
local QuestionService = require(script.Parent.QuestionService)
local RateLimiter = require(script.Parent.RateLimiter)

local ClassService = {}

local DIRECTORY_TTL_SECONDS = 3 * 24 * 60 * 60
local CACHE_TTL_SECONDS = 30
local MAX_DIRECTORY_RESULTS = 40
local MAX_LESSONS_PER_CLASS = 12
local MIN_QUESTIONS_PER_LESSON = 4
local MAX_QUESTIONS_PER_LESSON = 12

local classStore = DataStoreService:GetDataStore("Classes_v1")
local directories: { [string]: MemoryStoreSortedMap } = {}

type CacheEntry = { class: Types.Class, fetchedAt: number }
local cache: { [string]: CacheEntry } = {}

--- One sorted map per locale. Filtering by locale is then free, and each range
--- query stays small instead of scanning a global list to throw most of it away.
local function directoryFor(locale: string): MemoryStoreSortedMap
	local existing = directories[locale]
	if existing ~= nil then
		return existing
	end
	local map = MemoryStoreService:GetSortedMap(`ClassDirectory_v1_{locale}`)
	directories[locale] = map
	return map
end

local function capacityFor(player: Player): number
	local capacity = Economy.BaseClassCapacity
	if PurchaseService.ownsPass(player, "classCapacity") then
		capacity += Economy.CapacityPassBonus
	end
	return capacity
end

local function classLimitFor(player: Player): number
	local limit = Economy.BaseClassLimit
	if PurchaseService.ownsPass(player, "secondClass") then
		limit += Economy.SecondClassPassBonus
	end
	return limit
end

--- Promotion outranks everything else, which is what the teacher paid or watched
--- an ad for. It is bounded by time rather than by money, so it buys attention
--- for fifteen minutes, not a permanent seat at the top.
local function directoryScore(class: Types.Class): number
	local fill = if class.capacity > 0
		then math.clamp(#class.memberUserIds / class.capacity, 0, 1)
		else 0
	local score = math.floor(fill * 400) + math.floor(class.rating * 100)
	if class.promoUntil > os.time() then
		score += 1000
	end
	return score
end

--- The directory holds a summary, not the class. Lesson contents never belong in
--- a value that exists purely to be listed.
local function publish(class: Types.Class)
	task.spawn(function()
		pcall(function()
			directoryFor(class.locale):SetAsync(class.id, {
				id = class.id,
				subject = class.subject,
				title = class.title,
				grade = class.grade,
				teacherName = class.teacherName,
				members = #class.memberUserIds,
				capacity = class.capacity,
				rating = class.rating,
				ratingCount = class.ratingCount,
				lessonCount = (function()
					local count = 0
					for _ in class.lessons do
						count += 1
					end
					return count
				end)(),
				promoted = class.promoUntil > os.time(),
			}, DIRECTORY_TTL_SECONDS, directoryScore(class))
		end)
	end)
end

function ClassService.get(classId: string, fresh: boolean?): Types.Class?
	local entry = cache[classId]
	if not fresh and entry ~= nil and os.clock() - entry.fetchedAt < CACHE_TTL_SECONDS then
		return entry.class
	end

	local ok, value = pcall(function()
		return classStore:GetAsync(classId)
	end)
	if not ok or typeof(value) ~= "table" then
		return if entry ~= nil then entry.class else nil
	end

	local class = value :: Types.Class
	cache[classId] = { class = class, fetchedAt = os.clock() }
	return class
end

--- All writes go through UpdateAsync. Joining is the obvious reason: two players
--- on two servers taking the last seat is a race that a read-modify-write would
--- lose, and the fill rate feeds directly into what the teacher is paid.
---
--- The transform returning nil aborts the write, which is how "the class is full"
--- and "that class does not exist" are reported.
local function mutate(classId: string, transform: (Types.Class) -> Types.Class?): Types.Class?
	local result: Types.Class? = nil

	local ok = pcall(function()
		classStore:UpdateAsync(classId, function(current: any)
			if typeof(current) ~= "table" then
				return nil
			end
			local updated = transform(current :: Types.Class)
			if updated == nil then
				result = nil
				return nil
			end
			updated.updatedAt = os.time()
			result = updated
			return updated
		end)
	end)

	if not ok then
		return nil
	end
	if result ~= nil then
		cache[classId] = { class = result, fetchedAt = os.clock() }
		publish(result)
	end
	return result
end

function ClassService.create(
	player: Player,
	subject: unknown,
	title: unknown,
	grade: unknown
): (Types.Class?, string?)
	local data = DataService.getData(player)
	if data == nil then
		return nil, "notLoaded"
	end
	if not data.teacher.licensed then
		return nil, "notLicensed"
	end
	if typeof(subject) ~= "string" or Subjects.get(subject :: string) == nil then
		return nil, "unknownSubject"
	end
	if #data.teacher.classIds >= classLimitFor(player) then
		return nil, "classLimit"
	end

	if typeof(grade) ~= "number" then
		return nil, "badGrade"
	end
	local classGrade = math.clamp(math.floor(grade :: number), 1, Obstacles.MaxGrade)

	local cleanTitle = ModerationService.filterTitle(title, player.UserId)
	if cleanTitle == nil then
		return nil, "titleRejected"
	end

	local class: Types.Class = {
		id = HttpService:GenerateGUID(false),
		teacherUserId = player.UserId,
		teacherName = player.DisplayName,
		locale = data.locale,
		subject = subject :: string,
		title = cleanTitle,
		grade = classGrade,
		capacity = capacityFor(player),
		memberUserIds = {},
		lessons = {},
		rating = 0,
		ratingCount = 0,
		promoUntil = 0,
		createdAt = os.time(),
		updatedAt = os.time(),
	}

	local ok = pcall(function()
		classStore:SetAsync(class.id, class)
	end)
	if not ok then
		return nil, "storeFailed"
	end

	table.insert(data.teacher.classIds, class.id)
	cache[class.id] = { class = class, fetchedAt = os.clock() }
	publish(class)
	return class, nil
end

--- Returns false when the class could not be updated, in which case the student
--- is still enrolled and should try again.
---
--- The order matters more than it looks. Clearing the profile first and hoping
--- the write lands leaves a student who has left still counted among the
--- members -- and the member count is the fill rate, which is what the teacher is
--- paid on. Ghosts in a class are money.
function ClassService.leave(player: Player): boolean
	local data = DataService.getData(player)
	if data == nil then
		return false
	end
	local classId = data.enrolledClassId
	if classId == nil then
		return true
	end

	local updated = mutate(classId, function(current)
		local index = table.find(current.memberUserIds, player.UserId)
		if index ~= nil then
			table.remove(current.memberUserIds, index)
		end
		-- Not being in the list is success, not failure: the goal is to not be a
		-- member, and returning nil here would be indistinguishable from the
		-- write having failed.
		return current
	end)

	if updated == nil then
		return false
	end
	data.enrolledClassId = nil
	return true
end

function ClassService.join(player: Player, classId: unknown): (boolean, string?)
	if typeof(classId) ~= "string" then
		return false, "badRequest"
	end
	local id = classId :: string

	local data = DataService.getData(player)
	if data == nil then
		return false, "notLoaded"
	end
	if data.enrolledClassId == id then
		return true, nil
	end

	local class = ClassService.get(id)
	if class == nil then
		return false, "noClass"
	end
	-- A teacher in their own class would be paying themselves, and would know
	-- every question in it.
	if class.teacherUserId == player.UserId then
		return false, "ownClass"
	end

	-- Leaving has to actually succeed. Otherwise the student ends up counted in
	-- two classes at once, and both teachers are paid for a fuller room than they
	-- have.
	if data.enrolledClassId ~= nil and not ClassService.leave(player) then
		return false, "leaveFailed"
	end

	local updated = mutate(id, function(current)
		if table.find(current.memberUserIds, player.UserId) ~= nil then
			return current
		end
		if #current.memberUserIds >= current.capacity then
			return nil
		end
		table.insert(current.memberUserIds, player.UserId)
		return current
	end)

	if updated == nil then
		return false, "full"
	end
	data.enrolledClassId = id
	return true, nil
end

--- Ratings replace rather than accumulate, so a student who changes their mind
--- moves the average instead of voting twice.
function ClassService.rate(player: Player, classId: unknown, stars: unknown): (boolean, string?)
	if typeof(classId) ~= "string" or typeof(stars) ~= "number" then
		return false, "badRequest"
	end
	local id = classId :: string
	local score = math.clamp(math.floor(stars :: number), 1, Economy.MaxRating)

	local data = DataService.getData(player)
	if data == nil then
		return false, "notLoaded"
	end
	-- Only someone who took the class gets an opinion on it.
	if data.enrolledClassId ~= id then
		return false, "notEnrolled"
	end

	local previous = data.classRatings[id]
	local updated = mutate(id, function(current)
		local total = current.rating * current.ratingCount
		if previous ~= nil then
			total = total - previous + score
		else
			total += score
			current.ratingCount += 1
		end
		current.rating = if current.ratingCount > 0 then total / current.ratingCount else 0
		return current
	end)

	if updated == nil then
		return false, "failed"
	end
	data.classRatings[id] = score
	return true, nil
end

--- Extends a class's spotlight. Called from an ad reward or a purchase, and it
--- writes to the class rather than to the teacher's profile so the promotion
--- keeps running after they log off.
function ClassService.promote(player: Player, seconds: number)
	local data = DataService.getData(player)
	if data == nil then
		return
	end
	local classId = data.teacher.classIds[1]
	if classId == nil then
		return
	end

	mutate(classId, function(current)
		if current.teacherUserId ~= player.UserId then
			return nil
		end
		local from = math.max(current.promoUntil, os.time())
		current.promoUntil = from + seconds
		return current
	end)
end

function ClassService.addLesson(
	player: Player,
	classId: unknown,
	title: unknown,
	questionIds: unknown
): (string?, string?)
	if typeof(classId) ~= "string" or typeof(questionIds) ~= "table" then
		return nil, "badRequest"
	end
	local id = classId :: string
	local ids = questionIds :: { any }

	if #ids < MIN_QUESTIONS_PER_LESSON or #ids > MAX_QUESTIONS_PER_LESSON then
		return nil, "questionCount"
	end

	local class = ClassService.get(id, true)
	if class == nil then
		return nil, "noClass"
	end
	if class.teacherUserId ~= player.UserId then
		return nil, "notOwner"
	end

	local lessonCount = 0
	for _ in class.lessons do
		lessonCount += 1
	end
	if lessonCount >= MAX_LESSONS_PER_CLASS then
		return nil, "lessonLimit"
	end

	-- Every id is checked against the bank. A client sending ids for another
	-- subject, or ids that do not exist, gets nothing.
	local seen: { [string]: boolean } = {}
	local pool: { string } = {}
	local gradeTotal = 0
	for _, raw in ids do
		if typeof(raw) ~= "string" then
			return nil, "badQuestion"
		end
		local questionId = raw :: string
		if seen[questionId] then
			return nil, "duplicateQuestion"
		end
		-- Resolved through QuestionService rather than the bank directly, so a
		-- teacher's own published questions are usable and someone else's are not.
		-- A question still inside its hold does not resolve, so it cannot be
		-- slipped into a lesson ahead of publication.
		if not QuestionService.canUse(questionId, player.UserId) then
			return nil, "badQuestion"
		end
		local question = QuestionService.get(questionId)
		if question == nil or question.subject ~= class.subject then
			return nil, "badQuestion"
		end
		seen[questionId] = true
		gradeTotal += question.grade
		table.insert(pool, questionId)
	end

	local cleanTitle = ModerationService.filterTitle(title, player.UserId)
	if cleanTitle == nil then
		return nil, "titleRejected"
	end

	local lessonId = HttpService:GenerateGUID(false)
	local grade = math.max(1, math.floor(gradeTotal / #pool + 0.5))
	local drawCount = math.min(Economy.QuestionsPerLesson, #pool)

	local lesson: Types.Lesson = {
		id = lessonId,
		authorUserId = player.UserId,
		subject = class.subject,
		grade = grade,
		kind = "quiz",
		locale = class.locale,
		title = cleanTitle,
		body = "",
		-- Assembled entirely out of pre-moderated bank questions, with a title
		-- that has already been filtered, so there is nothing left to review.
		status = "published",
		translations = {},
		assembly = nil,
		test = {
			id = lessonId,
			subject = class.subject,
			grade = grade,
			draw = drawCount,
			poolIds = pool,
			passFraction = Economy.DefaultPassFraction,
		},
		obstacle = nil,
		createdAt = os.time(),
		publishedAt = os.time(),
	}

	local updated = mutate(id, function(current)
		current.lessons[lessonId] = lesson
		return current
	end)
	if updated == nil then
		return nil, "storeFailed"
	end
	return lessonId, nil
end

--- Recomputes a teacher's standing from the classes they actually run.
---
--- The classes are the source of truth for ratings, and the profile only caches
--- the aggregate -- a teacher is usually offline when someone rates them, so
--- there is nothing to write to at the moment it happens. Refreshing here means
--- the number is current whenever the teacher is looking at it or about to use
--- it, which is the only time it matters.
function ClassService.refreshTeacherRating(player: Player)
	local data = DataService.getData(player)
	if data == nil then
		return
	end

	local total = 0
	local count = 0
	for _, classId in data.teacher.classIds do
		local class = ClassService.get(classId)
		if class ~= nil and class.ratingCount > 0 then
			total += class.rating * class.ratingCount
			count += class.ratingCount
		end
	end

	data.teacher.rating = if count > 0 then total / count else 0
	data.teacher.ratingCount = count
end

--- An obstacle course: an ordered list of prefab module ids and a target grade.
---
--- Nothing here is text, so nothing here is moderated -- assembling prefabs is
--- outside the free-form rules entirely, and the course is live the moment it is
--- saved. The only thing standing between a teacher and a trivial course is the
--- grade window, which is deliberately checked here rather than left to the pass
--- rate: the quality factor needs twenty attempts to notice a too-easy course,
--- and those are twenty students who wasted their time.
function ClassService.addCourse(
	player: Player,
	classId: unknown,
	title: unknown,
	courseGrade: unknown,
	moduleIds: unknown
): (string?, string?)
	if typeof(classId) ~= "string" or typeof(moduleIds) ~= "table" then
		return nil, "badRequest"
	end
	if typeof(courseGrade) ~= "number" then
		return nil, "badGrade"
	end

	local id = classId :: string
	local class = ClassService.get(id, true)
	if class == nil then
		return nil, "noClass"
	end
	if class.teacherUserId ~= player.UserId then
		return nil, "notOwner"
	end
	if not Subjects.allows(class.subject, "obstacle") then
		return nil, "wrongSubject"
	end

	local lessonCount = 0
	for _ in class.lessons do
		lessonCount += 1
	end
	if lessonCount >= MAX_LESSONS_PER_CLASS then
		return nil, "lessonLimit"
	end

	local ids: { string } = {}
	for _, raw in moduleIds :: { any } do
		if typeof(raw) ~= "string" then
			return nil, "badModule"
		end
		table.insert(ids, raw :: string)
	end

	local grade = math.floor(courseGrade :: number)
	local validation = Obstacles.validateCourse(class.grade, grade, ids)
	if not validation.ok then
		return nil, validation.reason
	end

	local cleanTitle = ModerationService.filterTitle(title, player.UserId)
	if cleanTitle == nil then
		return nil, "titleRejected"
	end

	local lessonId = HttpService:GenerateGUID(false)
	local lesson: Types.Lesson = {
		id = lessonId,
		authorUserId = player.UserId,
		subject = class.subject,
		grade = grade,
		kind = "obstacle",
		locale = class.locale,
		title = cleanTitle,
		body = "",
		status = "published",
		translations = {},
		test = nil,
		assembly = nil,
		obstacle = { id = lessonId, moduleIds = ids, grade = grade },
		createdAt = os.time(),
		publishedAt = os.time(),
	}

	local updated = mutate(id, function(current)
		current.lessons[lessonId] = lesson
		return current
	end)
	if updated == nil then
		return nil, "storeFailed"
	end
	return lessonId, nil
end

--- An assembly lesson: a selection of tasks from the curated catalogue.
---
--- Same shape as the question constructor and for the same reason. The teacher
--- chooses what to set; the catalogue decides what is correct.
function ClassService.addAssembly(
	player: Player,
	classId: unknown,
	title: unknown,
	taskIds: unknown
): (string?, string?)
	if typeof(classId) ~= "string" or typeof(taskIds) ~= "table" then
		return nil, "badRequest"
	end
	local id = classId :: string
	local class = ClassService.get(id, true)
	if class == nil then
		return nil, "noClass"
	end
	if class.teacherUserId ~= player.UserId then
		return nil, "notOwner"
	end
	if not Subjects.allows(class.subject, "assembly") then
		return nil, "wrongSubject"
	end

	local lessonCount = 0
	for _ in class.lessons do
		lessonCount += 1
	end
	if lessonCount >= MAX_LESSONS_PER_CLASS then
		return nil, "lessonLimit"
	end

	local ids: { string } = {}
	local seen: { [string]: boolean } = {}
	local gradeTotal = 0
	for _, raw in taskIds :: { any } do
		if typeof(raw) ~= "string" or seen[raw] then
			return nil, "badTask"
		end
		local task = AssemblyService.get(raw :: string)
		if task == nil or task.subject ~= class.subject then
			return nil, "badTask"
		end
		seen[raw] = true
		gradeTotal += task.grade
		table.insert(ids, raw :: string)
	end
	if #ids == 0 or #ids > 8 then
		return nil, "taskCount"
	end

	local cleanTitle = ModerationService.filterTitle(title, player.UserId)
	if cleanTitle == nil then
		return nil, "titleRejected"
	end

	local lessonId = HttpService:GenerateGUID(false)
	local lesson: Types.Lesson = {
		id = lessonId,
		authorUserId = player.UserId,
		subject = class.subject,
		grade = math.max(1, math.floor(gradeTotal / #ids + 0.5)),
		kind = "assembly",
		locale = class.locale,
		title = cleanTitle,
		body = "",
		status = "published",
		translations = {},
		test = nil,
		obstacle = nil,
		assembly = { id = lessonId, taskIds = ids },
		createdAt = os.time(),
		publishedAt = os.time(),
	}

	local updated = mutate(id, function(current)
		current.lessons[lessonId] = lesson
		return current
	end)
	if updated == nil then
		return nil, "storeFailed"
	end
	return lessonId, nil
end

--- Ranked, highest first. Returns summaries; the caller resolves a class by id
--- when the player actually picks one.
function ClassService.list(locale: string, count: number?): { any }
	local wanted = math.clamp(count or MAX_DIRECTORY_RESULTS, 1, MAX_DIRECTORY_RESULTS)
	local ok, items = pcall(function()
		return directoryFor(locale):GetRangeAsync(Enum.SortDirection.Descending, wanted)
	end)
	if not ok or typeof(items) ~= "table" then
		return {}
	end

	local results: { any } = {}
	for _, item in items :: { any } do
		if typeof(item) == "table" and item.value ~= nil then
			table.insert(results, item.value)
		end
	end
	return results
end

local MAX_AUTHORING_RESULTS = 60

local function respond(player: Player, action: string, ok: boolean, reason: string?, payload: any?)
	Remotes.event(Remotes.Names.ClassResult):FireClient(player, {
		action = action,
		ok = ok,
		reason = reason,
		payload = payload,
	})
end

--- A class as its own teacher needs to see it, lessons included. Students get the
--- directory summary instead; there is no reason to ship them the question pools.
local function ownerView(class: Types.Class): any
	local lessons: { any } = {}
	for lessonId, lesson in class.lessons do
		table.insert(lessons, {
			id = lessonId,
			title = lesson.title,
			grade = lesson.grade,
			kind = lesson.kind,
			questionCount = if lesson.test ~= nil then #lesson.test.poolIds else 0,
			moduleCount = if lesson.obstacle ~= nil then #lesson.obstacle.moduleIds else 0,
		})
	end
	return {
		id = class.id,
		subject = class.subject,
		title = class.title,
		grade = class.grade,
		capacity = class.capacity,
		members = #class.memberUserIds,
		rating = class.rating,
		ratingCount = class.ratingCount,
		promoUntil = class.promoUntil,
		lessons = lessons,
	}
end

--- The lesson list a student sees for the class they are in. Question ids are
--- withheld: knowing which questions a lesson draws from is most of the value of
--- knowing the answers.
local function studentView(class: Types.Class): any
	local lessons: { any } = {}
	for lessonId, lesson in class.lessons do
		table.insert(lessons, {
			id = lessonId,
			title = lesson.title,
			grade = lesson.grade,
			kind = lesson.kind,
		})
	end
	return {
		id = class.id,
		subject = class.subject,
		title = class.title,
		grade = class.grade,
		teacherName = class.teacherName,
		members = #class.memberUserIds,
		capacity = class.capacity,
		rating = class.rating,
		ratingCount = class.ratingCount,
		lessons = lessons,
	}
end

local function onClassAction(player: Player, request: unknown)
	if typeof(request) ~= "table" then
		return
	end
	local message = request :: any
	local action = message.action
	if typeof(action) ~= "string" then
		return
	end

	-- Writes are metered far harder than reads: creating a class or adding a
	-- lesson costs a DataStore write, while listing costs a cached memory read.
	local isRead = action == "list"
		or action == "browseBank"
		or action == "mine"
		or action == "current"
		or action == "myQuestions"
		or action == "browseAssembly"
		or action == "campus"
	-- Submitting a question is six TextService calls and a store write, so it is
	-- metered harder than an ordinary write, which is itself metered harder than
	-- a cached read.
	local capacity, refill
	if action == "submitQuestion" then
		capacity, refill = 3, 0.1
	elseif isRead then
		capacity, refill = 10, 1
	else
		capacity, refill = 4, 0.2
	end
	if not RateLimiter.consume(player, `Class:{action}`, capacity, refill) then
		return
	end

	local data = DataService.getData(player)
	if data == nil then
		respond(player, action, false, "notLoaded")
		return
	end

	if action == "list" then
		respond(player, action, true, nil, ClassService.list(data.locale))
	elseif action == "join" then
		local ok, reason = ClassService.join(player, message.classId)
		local class = if ok then ClassService.get(message.classId :: string) else nil
		respond(player, action, ok, reason, if class ~= nil then studentView(class) else nil)
	elseif action == "leave" then
		respond(player, action, ClassService.leave(player), nil)
	elseif action == "rate" then
		local ok, reason = ClassService.rate(player, message.classId, message.stars)
		respond(player, action, ok, reason)
	elseif action == "current" then
		local classId = data.enrolledClassId
		local class = if classId ~= nil then ClassService.get(classId) else nil
		respond(player, action, class ~= nil, nil, if class ~= nil then studentView(class) else nil)
	elseif action == "create" then
		local class, reason =
			ClassService.create(player, message.subject, message.title, message.grade)
		respond(player, action, class ~= nil, reason, if class ~= nil then ownerView(class) else nil)
	elseif action == "mine" then
		ClassService.refreshTeacherRating(player)
		local views: { any } = {}
		for _, classId in data.teacher.classIds do
			local class = ClassService.get(classId)
			if class ~= nil then
				table.insert(views, ownerView(class))
			end
		end
		respond(player, action, true, nil, { classes = views, pending = data.teacher.pendingPayout })
	elseif action == "addCourse" then
		local lessonId, reason = ClassService.addCourse(
			player,
			message.classId,
			message.title,
			message.grade,
			message.moduleIds
		)
		respond(player, action, lessonId ~= nil, reason, lessonId)
	elseif action == "addAssembly" then
		local lessonId, reason =
			ClassService.addAssembly(player, message.classId, message.title, message.taskIds)
		respond(player, action, lessonId ~= nil, reason, lessonId)
	elseif action == "browseAssembly" then
		if not data.teacher.licensed then
			respond(player, action, false, "notLicensed")
			return
		end
		if typeof(message.subject) ~= "string" then
			respond(player, action, false, "badRequest")
			return
		end
		local grade = if typeof(message.grade) == "number" then message.grade else data.grade
		respond(
			player,
			action,
			true,
			nil,
			AssemblyService.listForAuthoring(message.subject, data.locale, grade)
		)
	elseif action == "addLesson" then
		local lessonId, reason =
			ClassService.addLesson(player, message.classId, message.title, message.questionIds)
		respond(player, action, lessonId ~= nil, reason, lessonId)
	elseif action == "browseBank" then
		if not data.teacher.licensed then
			respond(player, action, false, "notLicensed")
			return
		end
		local subject = message.subject
		if typeof(subject) ~= "string" or Subjects.get(subject) == nil then
			respond(player, action, false, "unknownSubject")
			return
		end
		local grade = if typeof(message.grade) == "number" then message.grade else data.grade
		respond(
			player,
			action,
			true,
			nil,
			BankService.listForAuthoring(subject, data.locale, grade, MAX_AUTHORING_RESULTS)
		)
	elseif action == "submitQuestion" then
		if not data.teacher.licensed then
			respond(player, action, false, "notLicensed")
			return
		end
		local questionId, reason = AuthoringService.submit(player, data.locale, message.draft)
		respond(player, action, questionId ~= nil, reason, questionId)
	elseif action == "myQuestions" then
		if not data.teacher.licensed then
			respond(player, action, false, "notLicensed")
			return
		end
		respond(player, action, true, nil, AuthoringService.listMine(player))
	elseif action == "campus" then
		respond(player, action, true, nil, CampusService.standings(data.locale))
	elseif action == "nominate" then
		-- Standing requires a rating, and the cached one may be stale.
		ClassService.refreshTeacherRating(player)
		local ok, reason = CampusService.nominate(player)
		respond(player, action, ok, reason)
	elseif action == "vote" then
		local ok, reason = CampusService.vote(player, message.candidateUserId)
		respond(player, action, ok, reason)
	elseif action == "subjectOfMonth" then
		local ok, reason = CampusService.setSubjectOfMonth(player, message.subject)
		respond(player, action, ok, reason)
	elseif action == "motto" then
		local ok, reason = CampusService.setMotto(player, message.motto)
		respond(player, action, ok, reason)
	elseif action == "startEvent" then
		local ok, reason = CampusService.startEvent(player)
		respond(player, action, ok, reason)
	elseif action == "appointDean" then
		local ok, reason =
			CampusService.appointDean(player, message.subject, message.teacherUserId)
		respond(player, action, ok, reason)
	elseif action == "reviewQuestion" then
		-- A dean rules on their own subject and nobody else's.
		if typeof(message.subject) ~= "string" then
			respond(player, action, false, "badRequest")
			return
		end
		if not CampusService.isDean(data.locale, message.subject, player.UserId) then
			respond(player, action, false, "notDean")
			return
		end
		if
			typeof(message.teacherUserId) ~= "number"
			or typeof(message.questionId) ~= "string"
		then
			respond(player, action, false, "badRequest")
			return
		end
		local applied = AuthoringService.review(
			math.floor(message.teacherUserId),
			message.questionId,
			message.subject,
			message.approve == true
		)
		respond(player, action, applied, if applied then nil else "notFound")
	elseif action == "collect" then
		respond(player, action, true, nil, PayoutService.collect(player))
	else
		respond(player, action, false, "unknownAction")
	end
end

function ClassService.start()
	Remotes.event(Remotes.Names.ClassAction).OnServerEvent:Connect(function(player, request)
		-- Every handler can yield on a DataStore or the text filter, so each
		-- request runs on its own thread rather than blocking the remote.
		task.spawn(onClassAction, player, request)
	end)
end

return ClassService
