--!strict
--- Funnel, economy and progression events.
---
--- Roblox's own AnalyticsService, so the numbers land in the Creator Hub rather
--- than in a spreadsheet nobody opens. There is no external sink and no API key.
---
--- This exists because the economy it measures has a dozen tunable constants --
--- the ad catch-up share, the decay rate, the quality band, the fill curve --
--- and every one of them was chosen by reasoning rather than by evidence. Without
--- these events the first tuning pass after launch would be guesswork with more
--- confidence than the guesswork that set them.
---
--- Every call is wrapped: analytics failing is never a reason for a lesson to
--- fail.

local AnalyticsService = game:GetService("AnalyticsService")
local HttpService = game:GetService("HttpService")
local Players = game:GetService("Players")

local Analytics = {}

--- The one funnel worth watching closely: what fraction of arrivals reach the
--- point where the game's actual loop has been experienced once.
local ONBOARDING = {
	joined = 1,
	lessonStarted = 2,
	lessonFinished = 3,
	lessonPassed = 4,
	classJoined = 5,
}

--- Funnel session ids per player, so a lesson's steps group together rather than
--- smearing across every attempt they ever make.
local lessonSessions: { [Player]: string } = {}
local reachedStep: { [Player]: { [string]: boolean } } = {}

local function safely(body: () -> ())
	local ok, err = pcall(body)
	if not ok then
		warn(`[school] analytics call failed: {err}`)
	end
end

--- Onboarding steps fire once per player, ever. Logging step two on their
--- fortieth lesson would make the funnel describe activity rather than progress.
local function once(player: Player, key: string): boolean
	local seen = reachedStep[player]
	if seen == nil then
		seen = {}
		reachedStep[player] = seen
	end
	if seen[key] then
		return false
	end
	seen[key] = true
	return true
end

function Analytics.playerJoined(player: Player)
	if not once(player, "joined") then
		return
	end
	safely(function()
		AnalyticsService:LogOnboardingFunnelStepEvent(player, ONBOARDING.joined, "joined")
	end)
end

function Analytics.lessonStarted(player: Player, subject: string, kind: string)
	lessonSessions[player] = HttpService:GenerateGUID(false)
	if once(player, "lessonStarted") then
		safely(function()
			AnalyticsService:LogOnboardingFunnelStepEvent(
				player,
				ONBOARDING.lessonStarted,
				"lessonStarted"
			)
		end)
	end
	safely(function()
		AnalyticsService:LogFunnelStepEvent(player, "lesson", lessonSessions[player], 1, "started", {
			subject = subject,
			kind = kind,
		})
	end)
end

function Analytics.lessonFinished(
	player: Player,
	subject: string,
	passed: boolean,
	score: number,
	total: number
)
	local session = lessonSessions[player]
	if session ~= nil then
		safely(function()
			AnalyticsService:LogFunnelStepEvent(player, "lesson", session, 2, "finished", {
				subject = subject,
				passed = tostring(passed),
			})
		end)
	end

	if once(player, "lessonFinished") then
		safely(function()
			AnalyticsService:LogOnboardingFunnelStepEvent(
				player,
				ONBOARDING.lessonFinished,
				"lessonFinished"
			)
		end)
	end
	if passed and once(player, "lessonPassed") then
		safely(function()
			AnalyticsService:LogOnboardingFunnelStepEvent(
				player,
				ONBOARDING.lessonPassed,
				"lessonPassed"
			)
		end)
	end

	safely(function()
		AnalyticsService:LogCustomEvent(player, "lessonScore", score, {
			subject = subject,
			total = tostring(total),
		})
	end)
end

function Analytics.classJoined(player: Player, subject: string)
	if once(player, "classJoined") then
		safely(function()
			AnalyticsService:LogOnboardingFunnelStepEvent(
				player,
				ONBOARDING.classJoined,
				"classJoined"
			)
		end)
	end
	safely(function()
		AnalyticsService:LogCustomEvent(player, "classJoined", 1, { subject = subject })
	end)
end

--- Where points come from and where they go. The soft currency is the dial the
--- whole economy turns on, so both directions are recorded.
function Analytics.pointsEarned(
	player: Player,
	amount: number,
	balance: number,
	source: string
)
	if amount <= 0 then
		return
	end
	safely(function()
		AnalyticsService:LogEconomyEvent(
			player,
			Enum.AnalyticsEconomyFlowType.Source,
			"points",
			amount,
			balance,
			source,
			source
		)
	end)
end

function Analytics.pointsSpent(player: Player, amount: number, balance: number, sink: string)
	if amount <= 0 then
		return
	end
	safely(function()
		AnalyticsService:LogEconomyEvent(
			player,
			Enum.AnalyticsEconomyFlowType.Sink,
			"points",
			amount,
			balance,
			sink,
			sink
		)
	end)
end

function Analytics.gradeReached(player: Player, grade: number)
	safely(function()
		AnalyticsService:LogProgressionEvent(
			player,
			"school",
			Enum.AnalyticsProgressionType.Complete,
			grade,
			`grade{grade}`
		)
	end)
end

function Analytics.graduated(player: Player, path: string, count: number)
	safely(function()
		AnalyticsService:LogCustomEvent(player, "graduated", count, { path = path })
	end)
end

--- The ad funnel in three steps. The gap between offered and watched is the
--- number that says whether the reward is worth the interruption; the gap
--- between watched and granted says whether receipts are arriving.
function Analytics.adOffered(player: Player, rewardId: string)
	safely(function()
		AnalyticsService:LogCustomEvent(player, "adOffered", 1, { reward = rewardId })
	end)
end

function Analytics.adResult(player: Player, rewardId: string, succeeded: boolean)
	safely(function()
		AnalyticsService:LogCustomEvent(player, "adResult", if succeeded then 1 else 0, {
			reward = rewardId,
		})
	end)
end

function Analytics.adGranted(player: Player, rewardId: string)
	safely(function()
		AnalyticsService:LogCustomEvent(player, "adGranted", 1, { reward = rewardId })
	end)
end

function Analytics.purchase(player: Player, kind: string, id: string, robux: number)
	safely(function()
		AnalyticsService:LogEconomyEvent(
			player,
			Enum.AnalyticsEconomyFlowType.Sink,
			"Robux",
			robux,
			0,
			kind,
			id
		)
	end)
end

function Analytics.teacherEvent(player: Player, name: string, value: number?)
	safely(function()
		AnalyticsService:LogCustomEvent(player, name, value or 1)
	end)
end

function Analytics.start()
	Players.PlayerRemoving:Connect(function(player: Player)
		lessonSessions[player] = nil
		reachedStep[player] = nil
	end)
end

return Analytics
