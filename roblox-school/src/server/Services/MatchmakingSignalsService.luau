--!strict
--- Publishes what this server is, so matchmaking can send it the right players.
---
--- Language is already a built-in Roblox signal and needs no code -- but its
--- weight does need raising in the Creator Hub, under Matchmaking, or servers
--- will stay as mixed as they are for a game where language does not matter. For
--- this game it decides whether a lesson is comprehensible at all, so it should
--- be weighted near the top.
---
--- What the built-in signals do not know is what year of school a server is
--- mostly running. A twelve-year-old dropped into a room of second-years finds
--- nothing to do, so that goes out as a custom attribute.
---
--- Both attributes must exist in the Creator Hub before they can be set; the API
--- rejects an attribute it has never heard of. Failing to publish a signal is not
--- worth disrupting a server over, so it is logged once and left alone.

local MatchmakingService = game:GetService("MatchmakingService")
local Players = game:GetService("Players")

local DataService = require(script.Parent.DataService)

local MatchmakingSignalsService = {}

local REFRESH_SECONDS = 30
local LOCALE_ATTRIBUTE = "Locale"
local GRADE_ATTRIBUTE = "AverageGrade"

local running = false
local warned = false

local function publish(name: string, value: any)
	local ok, err = pcall(function()
		MatchmakingService:SetServerAttribute(name, value)
	end)
	if not ok and not warned then
		warned = true
		warn(
			`[school] could not publish matchmaking attribute "{name}": {err}. `
				.. `Define it in the Creator Hub under Matchmaking before it can be set.`
		)
	end
end

local function refresh()
	local localeCounts: { [string]: number } = {}
	local gradeTotal = 0
	local counted = 0

	for _, player in Players:GetPlayers() do
		local data = DataService.getData(player)
		if data == nil then
			continue
		end
		local current: number = localeCounts[data.locale] or 0
		localeCounts[data.locale] = current + 1
		gradeTotal += data.grade
		counted += 1
	end

	if counted == 0 then
		return
	end

	-- The categorical signal wants one value, so a mixed server reports whichever
	-- language most of it speaks. Matchmaking then keeps feeding it that
	-- language, which is how a mixed server converges instead of staying mixed.
	local dominant, dominantCount = "", 0
	for locale, count in localeCounts do
		if count > dominantCount then
			dominant, dominantCount = locale, count
		end
	end

	publish(LOCALE_ATTRIBUTE, dominant)
	publish(GRADE_ATTRIBUTE, gradeTotal / counted)
end

function MatchmakingSignalsService.start()
	if running then
		return
	end
	running = true

	task.spawn(function()
		while running do
			pcall(refresh)
			task.wait(REFRESH_SECONDS)
		end
	end)

	game:BindToClose(function()
		running = false
	end)
end

return MatchmakingSignalsService
