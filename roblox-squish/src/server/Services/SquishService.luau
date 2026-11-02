--!strict
--- A player's squishes: shelves, pocket, income, squeezing, merging, selling.
---
--- Every coin in the game passes through here, and every amount is computed on
--- the server from the profile. The client sends intentions -- "merge this",
--- "put that on a shelf" -- never quantities.
---
--- Other services hook in rather than being imported: theft adds its prompt to
--- each shelf model through onShelfRendered, so this file knows nothing about
--- stealing and the two cannot form a require cycle.

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Economy = require(ReplicatedStorage.Shared.Config.Economy)
local Remotes = require(ReplicatedStorage.Shared.Remotes)
local SquishModel = require(ReplicatedStorage.Shared.Render.SquishModel)
local Squishes = require(ReplicatedStorage.Shared.Config.Squishes)
local Steal = require(ReplicatedStorage.Shared.Config.Steal)
local Types = require(ReplicatedStorage.Shared.Types)
local Analytics = require(script.Parent.AnalyticsService)
local DataService = require(script.Parent.DataService)
local PlotService = require(script.Parent.PlotService)
local PurchaseService = require(script.Parent.PurchaseService)
local RateLimiter = require(script.Parent.RateLimiter)

local SquishService = {}

--- Per squish, the last time it was squeezed (os.clock), for the cooldown.
local lastSqueeze: { [string]: number } = {}
--- Squishes that are out of their owner's base right now -- being carried or
--- bouncing loose. They stay in the owner's profile until a theft completes.
local inTransit: { [string]: boolean } = {}

type ShelfHook = (model: Model, owner: Player, squish: Types.Squish, favourite: boolean) -> ()
local shelfHooks: { ShelfHook } = {}

function SquishService.onShelfRendered(hook: ShelfHook)
	table.insert(shelfHooks, hook)
end

-- ---------------------------------------------------------------------------
-- Reading a profile
-- ---------------------------------------------------------------------------

function SquishService.totalSlots(player: Player, data: Types.ProfileData): number
	return Economy.totalSlots(data.boughtSlots, PurchaseService.ownsPass(player, "bigShelf"))
end

--- Slot of a squish, or nil when it is in the pocket.
function SquishService.slotOf(data: Types.ProfileData, uid: string): number?
	for slot, shelved in data.shelves do
		if shelved == uid then
			return tonumber(slot)
		end
	end
	return nil
end

function SquishService.freeSlot(player: Player, data: Types.ProfileData): number?
	for slot = 1, SquishService.totalSlots(player, data) do
		if data.shelves[tostring(slot)] == nil then
			return slot
		end
	end
	return nil
end

function SquishService.shelvedCount(data: Types.ProfileData): number
	local count = 0
	for _ in data.shelves do
		count += 1
	end
	return count
end

function SquishService.ownedCount(data: Types.ProfileData): number
	local count = 0
	for _ in data.squishes do
		count += 1
	end
	return count
end

--- The shelf as theft sees it: what is on it, and what each earns.
function SquishService.shelfEntries(data: Types.ProfileData): { Steal.ShelfEntry }
	local entries: { Steal.ShelfEntry } = {}
	for _, uid in data.shelves do
		local squish = data.squishes[uid]
		if squish ~= nil then
			table.insert(entries, { uid = uid, income = Economy.squishIncome(squish) })
		end
	end
	return entries
end

function SquishService.isInTransit(uid: string): boolean
	return inTransit[uid] == true
end

--- Base income: the shelves, before any multiplier.
function SquishService.baseIncome(data: Types.ProfileData): number
	local total = 0
	for _, uid in data.shelves do
		local squish = data.squishes[uid]
		if squish ~= nil then
			total += Economy.squishIncome(squish)
		end
	end
	return total
end

function SquishService.multiplier(player: Player, data: Types.ProfileData): number
	local now = os.time()
	return Economy.incomeMultiplier({
		incomePass = PurchaseService.ownsPass(player, "doubleCoins"),
		adBoost = (data.activeBoosts.ad or 0) > now,
		paidBoost = (data.activeBoosts.paid or 0) > now,
	})
end

-- ---------------------------------------------------------------------------
-- Changing a profile
-- ---------------------------------------------------------------------------

function SquishService.addCoins(player: Player, data: Types.ProfileData, amount: number, kind: string)
	data.coins += amount
	data.totalEarned += amount
	Analytics.coins(player, "source", amount, data.coins, kind)
end

function SquishService.spendCoins(player: Player, data: Types.ProfileData, amount: number, kind: string): boolean
	if data.coins < amount then
		return false
	end
	data.coins -= amount
	Analytics.coins(player, "sink", amount, data.coins, kind)
	return true
end

--- Records a squish as owned and puts it on the first free shelf, or in the
--- pocket. Returns the record and whether it went to the pocket.
function SquishService.give(
	player: Player,
	data: Types.ProfileData,
	species: string,
	tier: number,
	origin: Types.Origin,
	paid: boolean?
): (Types.Squish, boolean)
	local uid = `{player.UserId}-{data.nextUid}`
	data.nextUid += 1
	local squish: Types.Squish = {
		uid = uid,
		species = species,
		tier = tier,
		origin = origin,
		obtainedAt = os.time(),
		paid = if paid then true else nil,
	}
	data.squishes[uid] = squish
	local slot = SquishService.freeSlot(player, data)
	if slot ~= nil then
		data.shelves[tostring(slot)] = uid
	end
	return squish, slot == nil
end

--- Takes a squish out of a profile entirely. Returns the record.
function SquishService.take(data: Types.ProfileData, uid: string): Types.Squish?
	local squish = data.squishes[uid]
	if squish == nil then
		return nil
	end
	data.squishes[uid] = nil
	local slot = SquishService.slotOf(data, uid)
	if slot ~= nil then
		data.shelves[tostring(slot)] = nil
	end
	lastSqueeze[uid] = nil
	return squish
end

--- Lifts a shelved squish off its shelf for a theft: still owned, no longer
--- earning, no longer on display.
function SquishService.lift(data: Types.ProfileData, uid: string): boolean
	local slot = SquishService.slotOf(data, uid)
	if slot == nil then
		return false
	end
	data.shelves[tostring(slot)] = nil
	inTransit[uid] = true
	return true
end

--- Puts a lifted squish back: on a free shelf if there is one, else the pocket.
function SquishService.returnHome(player: Player, data: Types.ProfileData, uid: string)
	inTransit[uid] = nil
	if data.squishes[uid] == nil then
		return
	end
	local slot = SquishService.freeSlot(player, data)
	if slot ~= nil then
		data.shelves[tostring(slot)] = uid
	end
end

function SquishService.clearTransit(uid: string)
	inTransit[uid] = nil
end

-- ---------------------------------------------------------------------------
-- Showing it
-- ---------------------------------------------------------------------------

local function favouritesOf(data: Types.ProfileData): { [string]: boolean }
	return Steal.favourites(SquishService.shelfEntries(data))
end

--- Rebuilds the shelf models in a player's base. At most eighteen models, and
--- only on a change, so a full rebuild is simpler than diffing and costs
--- nothing anyone notices.
function SquishService.render(player: Player)
	local data = DataService.getData(player)
	local index = PlotService.plotIndex(player)
	if data == nil or index == nil then
		return
	end
	local folder = PlotService.model(index):FindFirstChild("Squishes") :: Folder
	local existing: { [string]: Model } = {}
	for _, child in folder:GetChildren() do
		local uid = child:GetAttribute("Uid")
		if child:IsA("Model") and typeof(uid) == "string" then
			existing[uid] = child
		end
	end

	local favourites = favouritesOf(data)
	for slotText, uid in data.shelves do
		local squish = data.squishes[uid]
		local slot = tonumber(slotText)
		if squish == nil or slot == nil then
			continue
		end
		local model = existing[uid]
		local favourite = favourites[uid] == true
		if model ~= nil and model:GetAttribute("Tier") == squish.tier and model:GetAttribute("Slot") == slot and model:GetAttribute("Favourite") == favourite then
			existing[uid] = nil
			continue
		end
		if model ~= nil then
			model:Destroy()
			existing[uid] = nil
		end
		model = SquishModel.build(squish.species, squish.tier)
		model.Name = uid
		model:SetAttribute("Uid", uid)
		model:SetAttribute("Slot", slot)
		model:SetAttribute("Favourite", favourite)
		model:SetAttribute("OwnerUserId", player.UserId)
		model:PivotTo(PlotService.slotCFrame(index, slot))

		local body = model.PrimaryPart :: BasePart
		local click = Instance.new("ClickDetector")
		click.MaxActivationDistance = 28
		click.Parent = body
		click.MouseClick:Connect(function(clicker: Player)
			SquishService.squeeze(clicker, uid)
		end)

		if favourite then
			local halo = Instance.new("Part")
			halo.Name = "Halo"
			halo.Shape = Enum.PartType.Cylinder
			halo.Size = Vector3.new(0.15, 1.6, 1.6)
			halo.Color = Color3.fromRGB(255, 220, 120)
			halo.Material = Enum.Material.Neon
			halo.Anchored = true
			halo.CanCollide = false
			halo.CanQuery = false
			halo.CFrame = body.CFrame * CFrame.new(0, body.Size.Y / 2 + 0.6, 0) * CFrame.Angles(0, 0, math.rad(90))
			halo.Parent = model
		end
		model.Parent = folder
		for _, hook in shelfHooks do
			task.spawn(hook, model, player, squish, favourite)
		end
	end
	for _, stale in existing do
		stale:Destroy()
	end
end

--- Everything the interface draws, in one message. Sent on any change.
function SquishService.push(player: Player)
	local data = DataService.getData(player)
	if data == nil then
		return
	end
	local favourites = favouritesOf(data)
	local list = {}
	for uid, squish in data.squishes do
		table.insert(list, {
			uid = uid,
			species = squish.species,
			tier = squish.tier,
			slot = SquishService.slotOf(data, uid),
			favourite = favourites[uid] == true,
			inTransit = inTransit[uid] == true,
			resale = Economy.resaleValue(squish),
		})
	end
	local now = os.time()
	Remotes.event(Remotes.Names.State):FireClient(player, {
		now = now,
		coins = math.floor(data.coins),
		income = SquishService.baseIncome(data) * SquishService.multiplier(player, data),
		multiplier = SquishService.multiplier(player, data),
		squishes = list,
		slots = SquishService.totalSlots(player, data),
		nextSlotCost = Economy.nextSlotCost(data.boughtSlots),
		traps = data.traps,
		shieldUntil = data.shieldUntil,
		protectedFor = if data.forfeitedProtection then 0 else math.max(0, Steal.NewbieProtectionSeconds - data.playSeconds),
		boosts = data.activeBoosts,
		pity = data.pity,
		boxesOpened = data.boxesOpened,
		onboardingDone = data.onboardingDone,
		plot = PlotService.plotIndex(player),
	})
end

--- Both of the above, which is what nearly every change wants.
function SquishService.refresh(player: Player)
	SquishService.render(player)
	SquishService.push(player)
end

-- ---------------------------------------------------------------------------
-- Player actions
-- ---------------------------------------------------------------------------

function SquishService.squeeze(player: Player, uid: string)
	local data = DataService.getData(player)
	if data == nil then
		return
	end
	-- Only the owner squeezes for coins. A visitor's tap does nothing at all,
	-- which also means nobody can farm someone else's shelf.
	local squish = data.squishes[uid]
	if squish == nil or SquishService.slotOf(data, uid) == nil then
		return
	end
	if not RateLimiter.consume(player, "squeeze", Economy.MaxSqueezesPerSecond, Economy.MaxSqueezesPerSecond) then
		return
	end
	local now = os.clock()
	if now - (lastSqueeze[uid] or -math.huge) < Economy.SqueezeCooldown then
		return
	end
	lastSqueeze[uid] = now

	local income = Economy.squishIncome(squish) * SquishService.multiplier(player, data)
	local reward = Economy.squeezeReward(income, PurchaseService.ownsPass(player, "comfyGloves"))
	SquishService.addCoins(player, data, reward, "squeeze")
	data.stats.squeezes = (data.stats.squeezes or 0) + 1
	Analytics.squeezed(player)

	-- The squash itself is drawn by every client watching; the attribute is
	-- the signal, and it carries the reward so the floating number matches.
	local index = PlotService.plotIndex(player)
	if index ~= nil then
		local model = (PlotService.model(index):FindFirstChild("Squishes") :: Folder):FindFirstChild(uid)
		if model ~= nil then
			model:SetAttribute("SqueezeReward", math.floor(reward))
			model:SetAttribute("SqueezedAt", workspace:GetServerTimeNow())
		end
	end
	Remotes.event(Remotes.Names.Coins):FireClient(player, math.floor(data.coins))
end

local function findMergePartner(data: Types.ProfileData, squish: Types.Squish): Types.Squish?
	local best: Types.Squish? = nil
	for uid, other in data.squishes do
		if uid ~= squish.uid and not inTransit[uid] and Economy.canMerge(squish, other) then
			-- Prefer a partner from the pocket, so a merge frees a shelf rather
			-- than leaving a gap the player has to notice.
			if best == nil or SquishService.slotOf(data, uid) == nil then
				best = other
			end
		end
	end
	return best
end

local actions: { [string]: (Player, Types.ProfileData, { [string]: any }) -> () } = {}

function actions.merge(player, data, request)
	local squish = data.squishes[request.uid]
	if squish == nil or inTransit[squish.uid] then
		return
	end
	local partner = findMergePartner(data, squish)
	if partner == nil then
		Remotes.toast(player, "base.noMerge")
		return
	end
	-- The squish the player picked survives, a tier up. If it was in the pocket
	-- and the partner was on a shelf, it takes the partner's shelf.
	local partnerSlot = SquishService.slotOf(data, partner.uid)
	SquishService.take(data, partner.uid)
	squish.tier += 1
	squish.origin = "merge"
	if partner.paid then
		squish.paid = true
	end
	if SquishService.slotOf(data, squish.uid) == nil and partnerSlot ~= nil then
		data.shelves[tostring(partnerSlot)] = squish.uid
	end
	data.stats.merges = (data.stats.merges or 0) + 1
	Analytics.merged(player, squish.species, squish.tier)
	Remotes.toast(player, "base.mergeDone", `@squish.{squish.species}`, squish.tier)
end

function actions.place(player, data, request)
	local uid = request.uid
	if data.squishes[uid] == nil or inTransit[uid] or SquishService.slotOf(data, uid) ~= nil then
		return
	end
	local slot = SquishService.freeSlot(player, data)
	if slot == nil then
		Remotes.toast(player, "base.shelvesFull")
		return
	end
	data.shelves[tostring(slot)] = uid
end

function actions.store(player, data, request)
	local slot = SquishService.slotOf(data, request.uid)
	if slot == nil then
		return
	end
	if SquishService.shelvedCount(data) <= 1 then
		Remotes.toast(player, "base.lastShelf")
		return
	end
	data.shelves[tostring(slot)] = nil
end

function actions.sell(player, data, request)
	local squish = data.squishes[request.uid]
	if squish == nil or inTransit[squish.uid] then
		return
	end
	if SquishService.slotOf(data, squish.uid) ~= nil and SquishService.shelvedCount(data) <= 1 then
		Remotes.toast(player, "base.lastShelf")
		return
	end
	local value = Economy.resaleValue(squish)
	SquishService.take(data, squish.uid)
	SquishService.addCoins(player, data, value, "resale")
end

function actions.buySlot(player, data, _request)
	local cost = Economy.nextSlotCost(data.boughtSlots)
	if cost == nil then
		return
	end
	if not SquishService.spendCoins(player, data, cost, "shelf") then
		Remotes.toast(player, "box.notEnough")
		return
	end
	data.boughtSlots += 1
end

--- Extra base actions owned by other services (trap upgrades), registered
--- rather than imported for the same reason as the shelf hooks.
function SquishService.registerAction(name: string, fn: (Player, Types.ProfileData, { [string]: any }) -> ())
	assert(actions[name] == nil, `duplicate base action {name}`)
	actions[name] = fn
end

local function onBaseAction(player: Player, request: unknown)
	if typeof(request) ~= "table" then
		return
	end
	local body = request :: { [string]: any }
	if typeof(body.action) ~= "string" or (body.uid ~= nil and typeof(body.uid) ~= "string") then
		return
	end
	if not RateLimiter.consume(player, "BaseAction", 8, 4) then
		return
	end
	local handler = actions[body.action]
	local data = DataService.getData(player)
	if handler == nil or data == nil then
		return
	end
	handler(player, data, body)
	SquishService.refresh(player)
end

-- ---------------------------------------------------------------------------

function SquishService.start()
	Remotes.event(Remotes.Names.BaseAction).OnServerEvent:Connect(onBaseAction)
	Remotes.event(Remotes.Names.OnboardingDone).OnServerEvent:Connect(function(player: Player)
		local data = DataService.getData(player)
		if data ~= nil then
			data.onboardingDone = true
		end
	end)

	PlotService.Claimed:Connect(function(player: Player)
		SquishService.refresh(player)
	end)

	-- Income. Paid once a second to every shelf, from the profile.
	task.spawn(function()
		while true do
			task.wait(Economy.TickSeconds)
			for _, player in Players:GetPlayers() do
				local data = DataService.getData(player)
				if data ~= nil and PlotService.plotIndex(player) ~= nil then
					local earned = SquishService.baseIncome(data) * SquishService.multiplier(player, data) * Economy.TickSeconds
					data.coins += earned
					data.totalEarned += earned
					Remotes.event(Remotes.Names.Coins):FireClient(player, math.floor(data.coins))
				end
			end
		end
	end)

	Players.PlayerRemoving:Connect(function(player: Player)
		local data = DataService.getData(player)
		if data ~= nil then
			for uid in data.squishes do
				lastSqueeze[uid] = nil
			end
		end
	end)

	-- A species id that no longer exists (renamed in a later version) would
	-- otherwise sit in a profile earning nothing and breaking the render.
	DataService.ProfileLoaded:Connect(function(_player: Player, data: Types.ProfileData)
		for uid, squish in data.squishes do
			if Squishes.get(squish.species) == nil then
				warn(`[squish] dropping unknown species {squish.species}`)
				SquishService.take(data, uid)
			end
		end
	end)
end

return SquishService
