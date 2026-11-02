--!strict
--- The last state the server sent, and a signal when it changes.
---
--- The interface never computes anything that matters. It draws this, and
--- sends intentions back.

local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Remotes = require(ReplicatedStorage.Shared.Remotes)

local State = {}

State.current = nil :: { [string]: any }?
--- os.clock() when the state arrived, paired with the server's os.time() in
--- it, so countdowns can be drawn without asking the server every second.
State.receivedAt = 0

local changed = Instance.new("BindableEvent")
State.Changed = changed.Event
local coinsChanged = Instance.new("BindableEvent")
State.CoinsChanged = coinsChanged.Event

--- Server time now, estimated from the last state.
function State.serverNow(): number
	local current = State.current
	if current == nil then
		return os.time()
	end
	return current.now + (os.clock() - State.receivedAt)
end

function State.init()
	Remotes.event(Remotes.Names.State).OnClientEvent:Connect(function(state)
		State.current = state
		State.receivedAt = os.clock()
		changed:Fire(state)
		coinsChanged:Fire(state.coins)
	end)
	Remotes.event(Remotes.Names.Coins).OnClientEvent:Connect(function(coins: number)
		local current = State.current
		if current ~= nil then
			current.coins = coins
		end
		coinsChanged:Fire(coins)
	end)
end

return State
