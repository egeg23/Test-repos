--!strict
--- What PolicyService allows for each player, asked once per session.
---
--- Two answers matter here, and both fail closed: when the policy service cannot
--- be reached, a player is treated as not allowed ads and as restricted from
--- paid random items. Showing an ad to a child or a paid box to a player in a
--- country that bans them is not an acceptable fallback for a network error.
---
---   * AreAdsAllowed is false for players under 13 and in some regions. Such a
---     player never sees an ad button -- not a disabled one, none at all.
---   * ArePaidRandomItemsRestricted is true where paid random items are not
---     allowed. Such a player never sees the Robux box, its odds or its button,
---     nor anything sold for Robux that multiplies coins, so for them coins are
---     never bought and the coin boxes stay free random items.
---   * IsPaidItemTradingAllowed is false where items bought with Robux may not
---     change hands. Such a player cannot give or receive a squish from the
---     Robux box in a trade.

local Players = game:GetService("Players")
local PolicyService = game:GetService("PolicyService")

local PolicyCache = {}

type Answer = { adsAllowed: boolean, paidRandomAllowed: boolean, paidTradingAllowed: boolean }

local cache: { [Player]: Answer } = {}

local function fetch(player: Player): Answer
	local cached = cache[player]
	if cached ~= nil then
		return cached
	end
	local answer: Answer = { adsAllowed = false, paidRandomAllowed = false, paidTradingAllowed = false }
	local ok, info = pcall(function()
		return PolicyService:GetPolicyInfoForPlayerAsync(player)
	end)
	if ok and typeof(info) == "table" then
		local policy = info :: any
		answer.adsAllowed = policy.AreAdsAllowed == true
		answer.paidRandomAllowed = policy.ArePaidRandomItemsRestricted == false
		answer.paidTradingAllowed = policy.IsPaidItemTradingAllowed == true
		-- Only a successful answer is cached; a failure is asked again next time.
		cache[player] = answer
	end
	return answer
end

function PolicyCache.adsAllowed(player: Player): boolean
	return fetch(player).adsAllowed
end

function PolicyCache.paidRandomAllowed(player: Player): boolean
	return fetch(player).paidRandomAllowed
end

--- Whether this player may trade items bought with Robux.
function PolicyCache.paidTradingAllowed(player: Player): boolean
	return fetch(player).paidTradingAllowed
end

function PolicyCache.start()
	Players.PlayerRemoving:Connect(function(player: Player)
		cache[player] = nil
	end)
end

return PolicyCache
