--!strict
--- Player-to-player trading.
---
--- Both sides see both offers; any change to either offer clears both
--- confirmations; after both confirm there is a short countdown during which
--- either can still back out. The server swaps the squishes in one step on the
--- one server both players are on, so a trade either happens whole or not at all.

local Types = require(script.Parent.Parent.Types)
local Economy = require(script.Parent.Economy)

local Trade = {}

Trade.MaxItemsPerSide = 4
--- Fresh accounts cannot trade. This stops a farm of throwaway accounts feeding
--- their starter squish to a main, and gives a new player time to learn what
--- things are worth before anyone can talk them out of them.
Trade.MinPlaySeconds = 30 * 60
Trade.ConfirmCountdown = 3
Trade.CooldownSeconds = 20
--- A squish that just changed hands cannot be traded straight on, so a stolen
--- one cannot be laundered to a friend in the same minute.
Trade.FreshLockSeconds = 10 * 60
Trade.RequestTimeout = 30

--- Validates one side's offer against the owner's collection.
function Trade.validateOffer(
	offer: { string },
	owned: { [string]: Types.Squish },
	now: number
): (boolean, string?)
	if #offer > Trade.MaxItemsPerSide then
		return false, "tooMany"
	end
	local seen: { [string]: boolean } = {}
	for _, uid in offer do
		if seen[uid] then
			return false, "duplicate"
		end
		seen[uid] = true
		local squish = owned[uid]
		if squish == nil then
			return false, "notOwned"
		end
		if (squish.origin == "stolen" or squish.origin == "trade") and now - squish.obtainedAt < Trade.FreshLockSeconds then
			return false, "fresh"
		end
	end
	return true, nil
end

function Trade.canTrade(playSeconds: number, lastTradeAt: number, now: number): (boolean, string?)
	if playSeconds < Trade.MinPlaySeconds then
		return false, "tooNew"
	end
	if now - lastTradeAt < Trade.CooldownSeconds then
		return false, "cooldown"
	end
	return true, nil
end

--- Room check: after the swap each side must still be under the cap on total
--- ownership.
function Trade.fits(ownedCount: number, giving: number, receiving: number): boolean
	return ownedCount - giving + receiving <= Economy.MaxOwned
end

return Trade
