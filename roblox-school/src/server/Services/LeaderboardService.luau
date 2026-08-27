--!strict
--- Weekly boards, per locale.
---
--- Retention has two halves and the game only had one. Achievements answer "what
--- am I working toward"; a board answers "how am I doing against everyone else",
--- which is the question that brings people back on a Monday. A school without
--- one is also missing the thing a school is actually famous for.
---
--- Three decisions worth stating, because each rules out an obvious alternative.
---
--- **Weekly, not all-time.** An all-time board is won once, in the first month,
--- by whoever was there first, and is thereafter a monument telling every new
--- player not to bother. A week is short enough that anyone can start from
--- nothing and finish somewhere.
---
--- **Per locale.** The campuses already are, for the same reason the elections
--- are: one global board is a Russian board with some other names on it, and
--- every smaller language loses its whole competitive layer.
---
--- **Ranked on what the player did this week, never on their balance.** A
--- balance board ranks who has bought the most and who has played longest since
--- launch. A weekly-activity board ranks this week, which is the only thing
--- anyone can still change.

local MemoryStoreService = game:GetService("MemoryStoreService")



local AchievementService = require(script.Parent.AchievementService)
local DataService = require(script.Parent.DataService)

local LeaderboardService = {}

--- How many rows a board keeps and shows. Ten is a board; a hundred is a
--- database with a scrollbar, and nobody reads past their own row anyway.
LeaderboardService.Size = 10

--- Entries expire rather than being cleared, so a week rolls over on its own and
--- there is no scheduled job that has to have run for the board to be correct.
--- Eight days, so the last day of a week is still readable on the first day of
--- the next one.
local ENTRY_TTL_SECONDS = 8 * 24 * 60 * 60

--- The boards, by what they rank. Each names the profile stat it reads, which
--- means a new board is a table entry rather than a new code path.
export type Board = { id: string, stat: string, displayKey: string }

LeaderboardService.Boards = {
	{ id = "lessons", stat = "lessonsPassed", displayKey = "board.lessons" },
	{ id = "courses", stat = "coursesFinished", displayKey = "board.courses" },
	{ id = "teaching", stat = "studentsTaught", displayKey = "board.teaching" },
} :: { Board }

local maps: { [string]: MemoryStoreSortedMap } = {}

local function weekNumber(): number
	return math.floor(os.time() / (7 * 24 * 60 * 60))
end

--- One sorted map per board, locale and week. The week is in the key rather than
--- in the value, so last week's board simply stops being read: nothing has to
--- delete it, and a server that was down over the rollover cannot corrupt it.
local function mapFor(boardId: string, locale: string): MemoryStoreSortedMap
	local key = `{boardId}_{locale}_{weekNumber()}`
	local existing = maps[key]
	if existing ~= nil then
		return existing
	end
	local map = MemoryStoreService:GetSortedMap(`Leaderboard_v1_{key}`)
	maps[key] = map
	return map
end

--- What this player has done this week, per board.
---
--- Held against a week stamp on the profile rather than as its own counter set:
--- the lifetime stats already exist and are already maintained, and a second set
--- of counters would be a second thing to keep in step. The baseline is what the
--- lifetime stat read at the start of the week; the week's score is the
--- difference.
local function weeklyScore(data: any, stat: string): number
	local baselines = data.weeklyBaselines
	if typeof(baselines) ~= "table" then
		return 0
	end
	local lifetime: number = data.stats[stat] or 0
	local baseline: number = baselines[stat] or 0
	return math.max(0, lifetime - baseline)
end

--- Resets the baselines when the week has turned over.
local function rollWeek(data: any)
	local week = weekNumber()
	if data.weeklyWeek == week and typeof(data.weeklyBaselines) == "table" then
		return
	end
	data.weeklyWeek = week
	local baselines: { [string]: number } = {}
	for _, board in LeaderboardService.Boards do
		baselines[board.stat] = data.stats[board.stat] or 0
	end
	data.weeklyBaselines = baselines
end

--- Writes this player's standing to the boards a given stat ranks.
---
--- `stat` is optional and narrows the write: bumping lessonsPassed changes one
--- board, and writing all three would be two wasted MemoryStore calls on every
--- lesson every player finishes. Omitting it writes all of them, which is what
--- a join wants.
---
--- Fire and forget: a board that fails to update is a cosmetic loss, and a
--- lesson must never fail because a MemoryStore call did.
function LeaderboardService.publish(player: Player, stat: string?)
	local data = DataService.getData(player)
	if data == nil then
		return
	end
	rollWeek(data)

	local locale = data.locale
	local name = player.DisplayName
	for _, board in LeaderboardService.Boards do
		if stat ~= nil and board.stat ~= stat then
			continue
		end
		local score = weeklyScore(data, board.stat)
		if score <= 0 then
			continue
		end
		task.spawn(function()
			pcall(function()
				mapFor(board.id, locale):SetAsync(
					tostring(player.UserId),
					{ name = name, score = score },
					ENTRY_TTL_SECONDS,
					score
				)
			end)
		end)
	end
end

--- The top rows of one board, plus where this player sits if they are not on it.
function LeaderboardService.read(player: Player, boardId: string): any
	local data = DataService.getData(player)
	if data == nil then
		return nil
	end

	local board: Board? = nil
	for _, candidate in LeaderboardService.Boards do
		if candidate.id == boardId then
			board = candidate
		end
	end
	if board == nil then
		return nil
	end

	rollWeek(data)

	local ok, items = pcall(function()
		return mapFor(board.id, data.locale)
			:GetRangeAsync(Enum.SortDirection.Descending, LeaderboardService.Size)
	end)

	local rows: { any } = {}
	local playerKey = tostring(player.UserId)
	local onBoard = false
	if ok and typeof(items) == "table" then
		for index, item in items :: { any } do
			local value = item.value
			if typeof(value) ~= "table" then
				continue
			end
			if item.key == playerKey then
				onBoard = true
			end
			table.insert(rows, {
				rank = index,
				name = value.name,
				score = value.score,
				isYou = item.key == playerKey,
			})
		end
	end

	return {
		id = board.id,
		displayKey = board.displayKey,
		rows = rows,
		-- Always sent, so a player who is not in the top ten still sees what they
		-- have done this week rather than an empty space where their row would be.
		yours = weeklyScore(data, board.stat),
		onBoard = onBoard,
	}
end

function LeaderboardService.start()
	AchievementService.setLeaderboard(LeaderboardService)

	DataService.ProfileLoaded:Connect(function(player: Player)
		local data = DataService.getData(player)
		if data ~= nil then
			rollWeek(data)
		end
		-- Published on join as well as on change, so a player who did nothing
		-- this session still appears with last session's total.
		task.spawn(LeaderboardService.publish, player)
	end)
end

return LeaderboardService
