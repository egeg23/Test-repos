--!strict
--- Speed and flight checks.
---
--- A character's physics belong to its own client, so a modified client can
--- run at any speed it likes and the server's WalkSpeed is only a suggestion.
--- This samples every character's root on the server and compares the distance
--- covered with what the speed the server set allows.
---
--- What happens on a violation is decided by whoever registered for it: theft
--- drops the carried squish and sends it home. On repeated violations the
--- character is also put back where it last was legitimately.
---
--- Knockbacks -- a pillow, a trampoline -- are legitimate bursts of speed, so
--- the services that cause them grant a short grace first.

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Steal = require(ReplicatedStorage.Shared.Config.Steal)

local MovementGuard = {}

local SAMPLE_SECONDS = 0.25
--- Tolerance over the expected speed: network jitter delivers positions in
--- bunches, and a few studs of slack keeps an honest laggy player clean.
local SPEED_TOLERANCE = 1.35
local DISTANCE_SLACK = 3
--- Strikes inside the window before the character is pulled back.
local STRIKES_TO_REWIND = 3
local STRIKE_WINDOW = 4
--- Studs above ground that count as flying while carrying. A jump reaches
--- about seven; a trampoline throw gets grace.
local CARRY_CEILING = 14

type Track = {
	lastPosition: Vector3,
	lastTime: number,
	safeCFrame: CFrame,
	graceUntil: number,
	expectedSpeed: number,
	strikes: { number },
}

local tracks: { [Player]: Track } = {}
local violationHandlers: { (Player, string) -> () } = {}
local carrying: { [Player]: boolean } = {}

function MovementGuard.onViolation(handler: (Player, string) -> ())
	table.insert(violationHandlers, handler)
end

local function rootOf(player: Player): BasePart?
	local character = player.Character
	if character == nil then
		return nil
	end
	return character:FindFirstChild("HumanoidRootPart") :: BasePart?
end

local function humanoidOf(player: Player): Humanoid?
	local character = player.Character
	if character == nil then
		return nil
	end
	return character:FindFirstChildOfClass("Humanoid")
end

--- Sets the speed the server expects and tells the humanoid. Only server
--- callers change it, so the check never trusts the client's own WalkSpeed.
function MovementGuard.setSpeed(player: Player, speed: number)
	local track = tracks[player]
	if track ~= nil then
		track.expectedSpeed = speed
	end
	local humanoid = humanoidOf(player)
	if humanoid ~= nil then
		humanoid.WalkSpeed = speed
	end
end

function MovementGuard.setCarrying(player: Player, value: boolean)
	carrying[player] = value or nil
end

function MovementGuard.grace(player: Player, seconds: number)
	local track = tracks[player]
	if track ~= nil then
		track.graceUntil = math.max(track.graceUntil, os.clock() + seconds)
	end
end

local function violate(player: Player, track: Track, reason: string, now: number)
	for _, handler in violationHandlers do
		task.spawn(handler, player, reason)
	end
	table.insert(track.strikes, now)
	while #track.strikes > 0 and now - track.strikes[1] > STRIKE_WINDOW do
		table.remove(track.strikes, 1)
	end
	if #track.strikes >= STRIKES_TO_REWIND then
		local character = player.Character
		if character ~= nil then
			character:PivotTo(track.safeCFrame)
		end
		track.strikes = {}
	end
end

local function sample(player: Player)
	local root = rootOf(player)
	if root == nil then
		tracks[player] = nil
		return
	end
	local now = os.clock()
	local track = tracks[player]
	if track == nil then
		tracks[player] = {
			lastPosition = root.Position,
			lastTime = now,
			safeCFrame = root.CFrame,
			graceUntil = now + 3,
			expectedSpeed = Steal.NormalWalkSpeed,
			strikes = {},
		}
		return
	end

	local elapsed = now - track.lastTime
	local moved = root.Position - track.lastPosition
	local horizontal = Vector3.new(moved.X, 0, moved.Z).Magnitude
	track.lastPosition = root.Position
	track.lastTime = now

	if now < track.graceUntil then
		track.safeCFrame = root.CFrame
		return
	end

	local allowed = track.expectedSpeed * SPEED_TOLERANCE * elapsed + DISTANCE_SLACK
	if horizontal > allowed then
		violate(player, track, "speed", now)
		return
	end
	if carrying[player] and root.Position.Y > CARRY_CEILING then
		violate(player, track, "height", now)
		return
	end
	track.safeCFrame = root.CFrame
end

function MovementGuard.start()
	Players.PlayerRemoving:Connect(function(player: Player)
		tracks[player] = nil
		carrying[player] = nil
	end)
	Players.PlayerAdded:Connect(function(player: Player)
		player.CharacterAdded:Connect(function()
			-- A respawn is a teleport; start the track fresh.
			tracks[player] = nil
			MovementGuard.setSpeed(player, Steal.NormalWalkSpeed)
		end)
	end)
	task.spawn(function()
		while true do
			task.wait(SAMPLE_SECONDS)
			for _, player in Players:GetPlayers() do
				sample(player)
			end
		end
	end)
end

return MovementGuard
