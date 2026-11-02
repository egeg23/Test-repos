--!strict
--- Theft, from the hold on the prompt to the squish landing on a new shelf.
---
--- Every decision is the server's:
---
---   * the prompt's hold time is measured here, from PromptButtonHoldBegan,
---     because a modified client can fire a prompt without holding it;
---   * the thief must be standing at the shelf when the hold ends;
---   * the victim must be robbable by the rules in Config/Steal, and the squish
---     must not be one of their favourites;
---   * carrying speed is set here and enforced by MovementGuard;
---   * delivery happens when the server sees the thief's root inside their own
---     walls, and only then does the squish change owner.
---
--- Until delivery the squish stays in the victim's profile, lifted off its
--- shelf. If anything goes wrong -- the thief leaves, cheats, times out, is
--- bonked -- it goes back. Nothing is ever in two profiles at once, and if the
--- victim leaves mid-carry the squish is simply in their pocket when they return.

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Base = require(ReplicatedStorage.Shared.Config.Base)
local Remotes = require(ReplicatedStorage.Shared.Remotes)
local SquishModel = require(ReplicatedStorage.Shared.Render.SquishModel)
local Steal = require(ReplicatedStorage.Shared.Config.Steal)
local Types = require(ReplicatedStorage.Shared.Types)
local Analytics = require(script.Parent.AnalyticsService)
local DataService = require(script.Parent.DataService)
local MovementGuard = require(script.Parent.MovementGuard)
local PlotService = require(script.Parent.PlotService)
local RateLimiter = require(script.Parent.RateLimiter)
local SquishService = require(script.Parent.SquishService)
local TrapService = require(script.Parent.TrapService)

local StealService = {}

local STEP_SECONDS = 0.2
--- A slipped squish cannot be grabbed again in the same instant; the bounce
--- has to be visible first.
local REGRAB_DELAY = 0.75

type Carry = {
	thief: Player,
	victim: Player,
	uid: string,
	species: string,
	tier: number,
	model: Model,
	startedAt: number,
	slowUntil: number,
}

type Loose = {
	victim: Player,
	uid: string,
	species: string,
	tier: number,
	model: Model,
	droppedAt: number,
}

local carries: { [Player]: Carry } = {}
local loose: { [string]: Loose } = {}
--- One theft per victim at a time: a base being robbed is busy.
local robbing: { [Player]: Player } = {}
local thiefReadyAt: { [Player]: number } = {}
local holdStarted: { [Player]: { [ProximityPrompt]: number } } = {}
local lastSwing: { [Player]: number } = {}

local random = Random.new()

local function rootOf(player: Player): BasePart?
	local character = player.Character
	if character == nil then
		return nil
	end
	return character:FindFirstChild("HumanoidRootPart") :: BasePart?
end

local function alive(player: Player): boolean
	local character = player.Character
	local humanoid = if character ~= nil then character:FindFirstChildOfClass("Humanoid") else nil
	return humanoid ~= nil and humanoid.Health > 0
end

local function today(): number
	return math.floor(os.time() / 86400)
end

local function rollDay(data: Types.ProfileData)
	if data.lossDay ~= today() then
		data.lossDay = today()
		data.lossesToday = 0
	end
end

local function carryState(player: Player, carrying: boolean, species: string?)
	Remotes.event(Remotes.Names.CarryState):FireClient(player, carrying, species)
end

--- Checks the thief's side: not already busy, cooled down, room at home.
local function thiefReady(thief: Player, thiefData: Types.ProfileData): (boolean, string?)
	if carries[thief] ~= nil then
		return false, "busy"
	end
	if os.clock() < (thiefReadyAt[thief] or 0) then
		return false, "busy"
	end
	if SquishService.freeSlot(thief, thiefData) == nil then
		return false, "noRoom"
	end
	return true, nil
end

local function victimState(victim: Player, data: Types.ProfileData): Steal.VictimState
	rollDay(data)
	return {
		playSeconds = data.playSeconds,
		forfeitedProtection = data.forfeitedProtection,
		shelved = SquishService.shelvedCount(data),
		shieldUntil = data.shieldUntil,
		lossesToday = data.lossesToday,
		online = victim.Parent == Players,
	}
end

local function attach(thief: Player, model: Model): boolean
	local character = thief.Character
	local head = if character ~= nil then character:FindFirstChild("Head") :: BasePart? else nil
	local body = model.PrimaryPart
	if head == nil or body == nil then
		return false
	end
	SquishModel.setFree(model, true)
	for _, child in model:GetDescendants() do
		if child:IsA("BasePart") then
			child.CanCollide = false
			child.Massless = true
		end
	end
	-- The pivot is the squish's bottom: sit it on top of the head.
	model:PivotTo(head.CFrame * CFrame.new(0, head.Size.Y / 2 + 0.2, 0))
	local weld = Instance.new("WeldConstraint")
	weld.Name = "CarryWeld"
	weld.Part0 = head
	weld.Part1 = body
	weld.Parent = body
	model.Parent = character
	return true
end

local function beginCarry(thief: Player, victim: Player, uid: string, species: string, tier: number): boolean
	local model = SquishModel.build(species, tier)
	model.Name = "Carried"
	if not attach(thief, model) then
		model:Destroy()
		return false
	end
	carries[thief] = {
		thief = thief,
		victim = victim,
		uid = uid,
		species = species,
		tier = tier,
		model = model,
		startedAt = os.clock(),
		slowUntil = 0,
	}
	robbing[victim] = thief
	MovementGuard.setSpeed(thief, Steal.carrySpeed(tier))
	MovementGuard.setCarrying(thief, true)
	TrapService.resetCarry(thief)
	carryState(thief, true, species)
	return true
end

--- Sends a lifted squish back to its owner's shelf.
local function goHome(victim: Player, uid: string, species: string)
	robbing[victim] = nil
	local data = DataService.getData(victim)
	if data == nil then
		SquishService.clearTransit(uid)
		return
	end
	SquishService.returnHome(victim, data, uid)
	SquishService.refresh(victim)
	Remotes.toast(victim, "steal.returned", `@squish.{species}`)
end

local function endCarry(carry: Carry)
	carries[carry.thief] = nil
	if carry.model.Parent ~= nil then
		carry.model:Destroy()
	end
	MovementGuard.setCarrying(carry.thief, false)
	MovementGuard.setSpeed(carry.thief, Steal.NormalWalkSpeed)
	carryState(carry.thief, false, nil)
end

local function cancelCarry(carry: Carry)
	endCarry(carry)
	goHome(carry.victim, carry.uid, carry.species)
end

local tryRegrab: (Player, Loose) -> ()

--- The squish springs out of the thief's arms and bounces. It goes home on
--- its own after a few seconds, at once if its owner touches it, and anyone
--- else may grab it in the meantime.
local function dropLoose(carry: Carry, toastKey: string)
	local model = carry.model
	endCarry(carry)
	local body = SquishModel.build(carry.species, carry.tier)
	body.Name = `Loose{carry.uid}`
	local origin = if model.PrimaryPart ~= nil then model.PrimaryPart.Position else Vector3.zero
	SquishModel.setFree(body, true)
	body:PivotTo(CFrame.new(origin + Vector3.new(0, 1, 0)))
	body.Parent = workspace
	local primary = body.PrimaryPart :: BasePart
	pcall(function()
		primary:SetNetworkOwner(nil)
	end)
	local angle = random:NextNumber() * math.pi * 2
	primary.AssemblyLinearVelocity = Vector3.new(math.cos(angle) * 18, 34, math.sin(angle) * 18)

	local entry: Loose = {
		victim = carry.victim,
		uid = carry.uid,
		species = carry.species,
		tier = carry.tier,
		model = body,
		droppedAt = os.clock(),
	}
	loose[carry.uid] = entry
	Remotes.toast(carry.thief, toastKey)

	primary.Touched:Connect(function(hit: BasePart)
		local character = hit:FindFirstAncestorOfClass("Model")
		local toucher = if character ~= nil then Players:GetPlayerFromCharacter(character) else nil
		if toucher == nil or loose[entry.uid] ~= entry then
			return
		end
		if toucher == entry.victim then
			loose[entry.uid] = nil
			body:Destroy()
			goHome(entry.victim, entry.uid, entry.species)
		elseif os.clock() - entry.droppedAt >= REGRAB_DELAY then
			tryRegrab(toucher, entry)
		end
	end)

	task.delay(Steal.LooseReturnSeconds, function()
		if loose[entry.uid] == entry then
			loose[entry.uid] = nil
			body:Destroy()
			goHome(entry.victim, entry.uid, entry.species)
		end
	end)
end

tryRegrab = function(toucher: Player, entry: Loose)
	local data = DataService.getData(toucher)
	if data == nil or not alive(toucher) then
		return
	end
	if not thiefReady(toucher, data) then
		return
	end
	loose[entry.uid] = nil
	entry.model:Destroy()
	if not beginCarry(toucher, entry.victim, entry.uid, entry.species, entry.tier) then
		goHome(entry.victim, entry.uid, entry.species)
	end
end

local function knockback(player: Player, velocity: Vector3)
	MovementGuard.grace(player, 1.5)
	Remotes.event(Remotes.Names.Knockback):FireClient(player, velocity)
end

local function deliver(carry: Carry)
	local thiefData = DataService.getData(carry.thief)
	local victimData = DataService.getData(carry.victim)
	if thiefData == nil or victimData == nil then
		cancelCarry(carry)
		return
	end
	endCarry(carry)
	robbing[carry.victim] = nil

	if random:NextNumber() < Steal.ReturnHomeChance then
		Remotes.toast(carry.thief, "steal.ranHome", `@squish.{carry.species}`)
		Analytics.theft(carry.thief, "ranHome")
		goHome(carry.victim, carry.uid, carry.species)
		return
	end

	local squish = SquishService.take(victimData, carry.uid)
	SquishService.clearTransit(carry.uid)
	if squish == nil then
		return
	end
	SquishService.give(carry.thief, thiefData, squish.species, squish.tier, "stolen", squish.paid)
	rollDay(victimData)
	victimData.lossesToday += 1
	victimData.shieldUntil = math.max(victimData.shieldUntil, os.time() + Steal.ShieldAfterTheftSeconds)
	thiefData.stats.steals = (thiefData.stats.steals or 0) + 1
	victimData.stats.stolenFrom = (victimData.stats.stolenFrom or 0) + 1
	thiefReadyAt[carry.thief] = os.clock() + Steal.ThiefCooldownSeconds

	Remotes.toast(carry.thief, "steal.delivered", `@squish.{squish.species}`)
	Remotes.toast(carry.victim, "steal.lost", carry.thief.DisplayName, `@squish.{squish.species}`)
	Analytics.theft(carry.thief, "delivered")
	SquishService.refresh(carry.thief)
	SquishService.refresh(carry.victim)
end

local function tryPickup(thief: Player, prompt: ProximityPrompt, owner: Player, uid: string)
	if thief == owner or not alive(thief) then
		return
	end
	local thiefData = DataService.getData(thief)
	local victimData = DataService.getData(owner)
	if thiefData == nil or victimData == nil then
		return
	end
	local squish = victimData.squishes[uid]
	if squish == nil or SquishService.slotOf(victimData, uid) == nil then
		return
	end

	-- The hold must really have happened, for as long as the prompt says.
	local holds = holdStarted[thief]
	local began = if holds ~= nil then holds[prompt] else nil
	if began == nil or os.clock() - began < Steal.holdSeconds(squish.tier) * 0.85 then
		return
	end
	(holds :: { [ProximityPrompt]: number })[prompt] = nil

	-- And the thief must be at the shelf.
	local root = rootOf(thief)
	local body = prompt.Parent
	if root == nil or body == nil or not body:IsA("BasePart") then
		return
	end
	if (root.Position - body.Position).Magnitude > Steal.PromptDistance + Steal.DistanceSlack then
		return
	end

	local ready, why = thiefReady(thief, thiefData)
	if not ready then
		Remotes.toast(thief, `steal.reason.{why}`)
		return
	end
	if robbing[owner] ~= nil then
		Remotes.toast(thief, "steal.reason.shield")
		return
	end
	local allowed, reason = Steal.canBeRobbed(victimState(owner, victimData), os.time())
	if not allowed then
		Remotes.toast(thief, `steal.reason.{reason}`)
		return
	end
	if Steal.favourites(SquishService.shelfEntries(victimData))[uid] then
		return
	end

	if not SquishService.lift(victimData, uid) then
		return
	end
	if not beginCarry(thief, owner, uid, squish.species, squish.tier) then
		SquishService.returnHome(owner, victimData, uid)
		return
	end
	-- Stealing ends a newbie's protection: it is a truce, not a head start.
	if thiefData.playSeconds < Steal.NewbieProtectionSeconds then
		thiefData.forfeitedProtection = true
	end
	SquishService.refresh(owner)
	SquishService.push(thief)
	Remotes.toast(owner, "steal.robbed", thief.DisplayName, `@squish.{squish.species}`)
	Analytics.theft(thief, "pickup")
end

--- Adds the grab prompt to a shelf model. Favourites get none.
local function onShelfRendered(model: Model, owner: Player, squish: Types.Squish, favourite: boolean)
	if favourite then
		return
	end
	local body = model.PrimaryPart
	if body == nil then
		return
	end
	local prompt = Instance.new("ProximityPrompt")
	prompt.Name = "StealPrompt"
	prompt:SetAttribute("TextKey", "steal.action")
	prompt:SetAttribute("SquishKey", `squish.{squish.species}`)
	prompt:SetAttribute("OwnerUserId", owner.UserId)
	prompt.ActionText = ""
	prompt.HoldDuration = Steal.holdSeconds(squish.tier)
	prompt.MaxActivationDistance = Steal.PromptDistance
	prompt.RequiresLineOfSight = false
	prompt.Parent = body
	local uid = squish.uid
	prompt.PromptButtonHoldBegan:Connect(function(player: Player)
		local holds = holdStarted[player]
		if holds == nil then
			holds = {}
			holdStarted[player] = holds
		end
		holds[prompt] = os.clock()
	end)
	prompt.PromptButtonHoldEnded:Connect(function(player: Player)
		local holds = holdStarted[player]
		if holds ~= nil then
			-- Ended fires after Triggered on a completed hold, so clearing here
			-- only matters for a hold that was let go early.
			task.defer(function()
				holds[prompt] = nil
			end)
		end
	end)
	prompt.Triggered:Connect(function(player: Player)
		tryPickup(player, prompt, owner, uid)
	end)
end

-- ---------------------------------------------------------------------------

local function step(carry: Carry)
	local thief = carry.thief
	local root = rootOf(thief)
	if root == nil or not alive(thief) or carry.model.Parent == nil then
		cancelCarry(carry)
		return
	end
	if carry.victim.Parent ~= Players then
		endCarry(carry)
		SquishService.clearTransit(carry.uid)
		return
	end
	if os.clock() - carry.startedAt > Steal.CarryTimeoutSeconds then
		Remotes.toast(thief, "steal.ranHome", `@squish.{carry.species}`)
		cancelCarry(carry)
		return
	end

	-- Slipping: a per-second chance, applied per step.
	if random:NextNumber() < Steal.slipChancePerSecond(carry.tier) * STEP_SECONDS then
		dropLoose(carry, "steal.slipped")
		return
	end

	-- The victim's traps.
	local victimPlot = PlotService.plotIndex(carry.victim)
	if victimPlot ~= nil then
		local effect = TrapService.step(thief, victimPlot, root.Position)
		if effect.knockLoose then
			dropLoose(carry, "steal.knocked")
			return
		end
		if effect.bounce then
			knockback(thief, TrapService.bounceVelocity(victimPlot))
		end
		if effect.slowFactor ~= nil and effect.slowSeconds ~= nil then
			carry.slowUntil = os.clock() + effect.slowSeconds
			MovementGuard.setSpeed(thief, Steal.carrySpeed(carry.tier) * effect.slowFactor)
		end
	end
	if carry.slowUntil > 0 and os.clock() >= carry.slowUntil then
		carry.slowUntil = 0
		MovementGuard.setSpeed(thief, Steal.carrySpeed(carry.tier))
	end

	-- Home?
	local home = PlotService.plotIndex(thief)
	if home ~= nil then
		local x, z = PlotService.toLocal(home, root.Position)
		if Base.insideWalls(x, z) then
			deliver(carry)
		end
	end
end

local function swing(player: Player)
	if not RateLimiter.consume(player, "pillow", 2, 1 / Steal.PillowCooldown) then
		return
	end
	local now = os.clock()
	if now - (lastSwing[player] or 0) < Steal.PillowCooldown then
		return
	end
	lastSwing[player] = now
	local root = rootOf(player)
	if root == nil then
		return
	end
	for target, carry in carries do
		if target ~= player then
			local targetRoot = rootOf(target)
			if targetRoot ~= nil and (targetRoot.Position - root.Position).Magnitude <= Steal.PillowRange then
				local away = targetRoot.Position - root.Position
				local flat = Vector3.new(away.X, 0, away.Z)
				local direction = if flat.Magnitude > 0.01 then flat.Unit else root.CFrame.LookVector
				dropLoose(carry, "steal.knocked")
				knockback(target, direction * Steal.PillowKnockback + Vector3.new(0, 25, 0))
				return
			end
		end
	end
end

local function givePillow(player: Player, character: Model)
	local backpack = player:WaitForChild("Backpack", 10)
	if backpack == nil or character.Parent == nil then
		return
	end
	local tool = Instance.new("Tool")
	tool.Name = "Pillow"
	tool.CanBeDropped = false
	tool.RequiresHandle = true
	local handle = Instance.new("Part")
	handle.Name = "Handle"
	handle.Size = Vector3.new(2.2, 0.9, 1.6)
	handle.Color = Color3.fromRGB(255, 214, 230)
	handle.Material = Enum.Material.SmoothPlastic
	handle.CanCollide = false
	handle.Parent = tool
	tool.Activated:Connect(function()
		swing(player)
	end)
	tool.Parent = backpack
end

function StealService.isCarrying(player: Player): boolean
	return carries[player] ~= nil
end

function StealService.start()
	SquishService.onShelfRendered(onShelfRendered)

	MovementGuard.onViolation(function(player: Player, _reason: string)
		local carry = carries[player]
		if carry ~= nil then
			-- A cheating carrier gets nothing: the squish goes straight home.
			cancelCarry(carry)
			Analytics.theft(player, "movementViolation")
		end
	end)

	Players.PlayerAdded:Connect(function(player: Player)
		player.CharacterAdded:Connect(function(character)
			givePillow(player, character)
		end)
	end)
	for _, player in Players:GetPlayers() do
		if player.Character ~= nil then
			task.spawn(givePillow, player, player.Character)
		end
	end

	Players.PlayerRemoving:Connect(function(player: Player)
		local carry = carries[player]
		if carry ~= nil then
			cancelCarry(carry)
		end
		-- A victim leaving: whatever was lifted from them stays in their
		-- profile, off the shelf, which is the pocket.
		for thief, other in carries do
			if other.victim == player then
				endCarry(other)
				SquishService.clearTransit(other.uid)
				Remotes.toast(thief, "steal.ranHome", `@squish.{other.species}`)
			end
		end
		for uid, entry in loose do
			if entry.victim == player then
				loose[uid] = nil
				entry.model:Destroy()
				SquishService.clearTransit(uid)
			end
		end
		robbing[player] = nil
		thiefReadyAt[player] = nil
		holdStarted[player] = nil
		lastSwing[player] = nil
	end)

	task.spawn(function()
		while true do
			task.wait(STEP_SECONDS)
			for _, carry in carries do
				step(carry)
			end
		end
	end)
end

return StealService
