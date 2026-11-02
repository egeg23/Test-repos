--!strict
--- Player-to-player trading, both sides confirming.
---
--- A trade is a small state machine on the server:
---
---   requested -> open -> (both confirmed) -> countdown -> done
---
--- Any change to either offer clears both confirmations, so nobody can swap
--- an item out after the other side said yes. During the countdown either
--- side can still cancel. The swap itself happens in one step between two
--- profiles on this server, after every rule is checked again against the
--- profiles as they are at that moment.

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Remotes = require(ReplicatedStorage.Shared.Remotes)
local Trade = require(ReplicatedStorage.Shared.Config.Trade)
local Types = require(ReplicatedStorage.Shared.Types)
local DataService = require(script.Parent.DataService)
local PolicyCache = require(script.Parent.PolicyCache)
local RateLimiter = require(script.Parent.RateLimiter)
local SquishService = require(script.Parent.SquishService)

local TradeService = {}

type Session = {
	a: Player,
	b: Player,
	state: "requested" | "open" | "countdown",
	offers: { [Player]: { string } },
	confirmed: { [Player]: boolean },
	requestedAt: number,
	countdownId: number,
}

local sessions: { [Player]: Session } = {}

local function other(session: Session, player: Player): Player
	return if session.a == player then session.b else session.a
end

local function describe(session: Session, viewer: Player): { [string]: any }
	local partner = other(session, viewer)
	local function items(owner: Player): { any }
		local data = DataService.getData(owner)
		local list = {}
		for _, uid in session.offers[owner] do
			local squish = if data ~= nil then data.squishes[uid] else nil
			if squish ~= nil then
				table.insert(list, { uid = uid, species = squish.species, tier = squish.tier })
			end
		end
		return list
	end
	return {
		state = session.state,
		partner = partner.DisplayName,
		partnerUserId = partner.UserId,
		incoming = session.state == "requested" and session.b == viewer,
		mine = items(viewer),
		theirs = items(partner),
		myConfirm = session.confirmed[viewer] == true,
		theirConfirm = session.confirmed[partner] == true,
	}
end

local function broadcast(session: Session)
	for _, player in { session.a, session.b } do
		Remotes.event(Remotes.Names.TradeState):FireClient(player, describe(session, player))
	end
end

local function close(session: Session, toastKey: string?)
	for _, player in { session.a, session.b } do
		if sessions[player] == session then
			sessions[player] = nil
		end
		if player.Parent == Players then
			Remotes.event(Remotes.Names.TradeState):FireClient(player, nil)
			if toastKey ~= nil then
				Remotes.toast(player, toastKey)
			end
		end
	end
end

local function reject(player: Player, reason: string?)
	Remotes.toast(player, `trade.reason.{reason or "busy"}`)
end

--- Every rule, against both profiles as they are now.
local function validate(session: Session): (boolean, Player?, string?)
	local now = os.time()
	local paidTrading = PolicyCache.paidTradingAllowed(session.a) and PolicyCache.paidTradingAllowed(session.b)
	for _, player in { session.a, session.b } do
		local data = DataService.getData(player)
		if data == nil then
			return false, player, "notOwned"
		end
		local ok, reason = Trade.validateOffer(session.offers[player], data.squishes, now, paidTrading)
		if not ok then
			return false, player, reason
		end
		for _, uid in session.offers[player] do
			if SquishService.isInTransit(uid) then
				return false, player, "notOwned"
			end
		end
		-- Giving away shelved squishes must leave at least one on a shelf.
		local shelvedGiven = 0
		for _, uid in session.offers[player] do
			if SquishService.slotOf(data, uid) ~= nil then
				shelvedGiven += 1
			end
		end
		if shelvedGiven > 0 and SquishService.shelvedCount(data) - shelvedGiven < 1 then
			return false, player, "lastSquish"
		end
		local partner = other(session, player)
		if not Trade.fits(SquishService.ownedCount(data), #session.offers[player], #session.offers[partner]) then
			return false, player, "full"
		end
	end
	return true, nil, nil
end

local function execute(session: Session)
	local ok, who, reason = validate(session)
	if not ok then
		if who ~= nil then
			reject(who, reason)
			reject(other(session, who), reason)
		end
		close(session, "trade.cancelled")
		return
	end
	local dataA = DataService.getData(session.a) :: Types.ProfileData
	local dataB = DataService.getData(session.b) :: Types.ProfileData
	local fromA: { Types.Squish } = {}
	local fromB: { Types.Squish } = {}
	for _, uid in session.offers[session.a] do
		table.insert(fromA, SquishService.take(dataA, uid) :: Types.Squish)
	end
	for _, uid in session.offers[session.b] do
		table.insert(fromB, SquishService.take(dataB, uid) :: Types.Squish)
	end
	for _, squish in fromA do
		SquishService.give(session.b, dataB, squish.species, squish.tier, "trade", squish.paid)
	end
	for _, squish in fromB do
		SquishService.give(session.a, dataA, squish.species, squish.tier, "trade", squish.paid)
	end
	local now = os.time()
	dataA.lastTradeAt = now
	dataB.lastTradeAt = now
	-- Save both now. Two profiles changed together; leaving it to autosave
	-- widens the window in which a crash keeps one half of the swap.
	for _, player in { session.a, session.b } do
		local profile = DataService.get(player)
		if profile ~= nil and profile:IsActive() then
			pcall(function()
				profile:Save()
			end)
		end
		SquishService.refresh(player)
	end
	close(session, "trade.done")
end

local handlers: { [string]: (Player, { [string]: any }) -> () } = {}

function handlers.request(player, body)
	local target = Players:GetPlayerByUserId(tonumber(body.userId) or 0)
	if target == nil or target == player then
		return
	end
	if sessions[player] ~= nil or sessions[target] ~= nil then
		reject(player, "busy")
		return
	end
	local now = os.time()
	for _, side in { player, target } do
		local data = DataService.getData(side)
		if data == nil then
			return
		end
		local ok, reason = Trade.canTrade(data.playSeconds, data.lastTradeAt, now)
		if not ok then
			reject(player, reason)
			return
		end
	end
	local session: Session = {
		a = player,
		b = target,
		state = "requested",
		offers = { [player] = {}, [target] = {} },
		confirmed = {},
		requestedAt = os.clock(),
		countdownId = 0,
	}
	sessions[player] = session
	sessions[target] = session
	broadcast(session)
	task.delay(Trade.RequestTimeout, function()
		if session.state == "requested" and sessions[player] == session then
			close(session, "trade.cancelled")
		end
	end)
end

function handlers.accept(player, _body)
	local session = sessions[player]
	if session == nil or session.state ~= "requested" or session.b ~= player then
		return
	end
	session.state = "open"
	broadcast(session)
end

function handlers.cancel(player, _body)
	local session = sessions[player]
	if session ~= nil then
		close(session, "trade.cancelled")
	end
end

function handlers.offer(player, body)
	local session = sessions[player]
	if session == nil or session.state == "requested" then
		return
	end
	if typeof(body.uids) ~= "table" then
		return
	end
	local uids: { string } = {}
	for _, uid in body.uids do
		if typeof(uid) == "string" then
			table.insert(uids, uid)
		end
	end
	local data = DataService.getData(player)
	if data == nil then
		return
	end
	local paidTrading = PolicyCache.paidTradingAllowed(session.a) and PolicyCache.paidTradingAllowed(session.b)
	local ok, reason = Trade.validateOffer(uids, data.squishes, os.time(), paidTrading)
	if not ok then
		reject(player, reason)
		return
	end
	session.offers[player] = uids
	-- A changed offer un-confirms both sides and stops a running countdown.
	session.confirmed = {}
	session.state = "open"
	session.countdownId += 1
	broadcast(session)
end

function handlers.confirm(player, _body)
	local session = sessions[player]
	if session == nil or session.state ~= "open" then
		return
	end
	session.confirmed[player] = true
	if session.confirmed[session.a] and session.confirmed[session.b] then
		session.state = "countdown"
		session.countdownId += 1
		local id = session.countdownId
		broadcast(session)
		task.delay(Trade.ConfirmCountdown, function()
			if session.state == "countdown" and session.countdownId == id and sessions[session.a] == session then
				execute(session)
			end
		end)
	else
		broadcast(session)
	end
end

local function onTradeAction(player: Player, body: unknown)
	if typeof(body) ~= "table" then
		return
	end
	local request = body :: { [string]: any }
	if not RateLimiter.consume(player, "TradeAction", 6, 2) then
		return
	end
	local handler = handlers[request.action]
	if handler ~= nil then
		handler(player, request)
	end
end

function TradeService.start()
	Remotes.event(Remotes.Names.TradeAction).OnServerEvent:Connect(onTradeAction)
	Players.PlayerRemoving:Connect(function(player: Player)
		local session = sessions[player]
		if session ~= nil then
			close(session, "trade.cancelled")
		end
	end)
end

return TradeService
