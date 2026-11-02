--!strict
--- Opening blind boxes.
---
--- The roll uses Config/Boxes, the same function the odds panel reads from and
--- the tests measure. The server rolls; the client only animates what it was
--- told. The very first box a player opens is a free caramel box that always
--- holds the starter squish, so the first minute ends with something on a
--- shelf to squeeze.

local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Boxes = require(ReplicatedStorage.Shared.Config.Boxes)
local Economy = require(ReplicatedStorage.Shared.Config.Economy)
local Remotes = require(ReplicatedStorage.Shared.Remotes)
local Squishes = require(ReplicatedStorage.Shared.Config.Squishes)
local Types = require(ReplicatedStorage.Shared.Types)
local Analytics = require(script.Parent.AnalyticsService)
local DataService = require(script.Parent.DataService)
local RateLimiter = require(script.Parent.RateLimiter)
local SquishService = require(script.Parent.SquishService)

local BoxService = {}

local FIRST_BOX = "caramel"

local random = Random.new()
local function rng(): number
	return random:NextNumber()
end

--- Rolls and grants one box's squish. Returns false only when nothing was
--- granted.
local function grant(player: Player, data: Types.ProfileData, box: Boxes.Box, free: boolean): boolean
	local species: Squishes.Species?
	local rarity: Types.Rarity
	if free then
		species = Squishes.get(Economy.StarterSpecies)
		rarity = "common"
	else
		local nextCount
		rarity, nextCount = Boxes.rollRarity(box, data.pity[box.id] or 0, rng)
		data.pity[box.id] = nextCount
		species = Boxes.rollSpecies(rarity, rng)
	end
	if species == nil then
		return false
	end
	local squish, toPocket = SquishService.give(player, data, species.id, 1, "box", box.paid)
	data.boxesOpened += 1
	data.starterGiven = true
	Analytics.boxOpened(player, box.id, rarity, data.boxesOpened)
	Remotes.event(Remotes.Names.Unboxed):FireClient(player, box.id, squish.species, rarity, toPocket)
	SquishService.refresh(player)
	return true
end

local function onOpenBox(player: Player, boxId: unknown)
	if typeof(boxId) ~= "string" then
		return
	end
	if not RateLimiter.consume(player, "OpenBox", 3, 1) then
		return
	end
	local data = DataService.getData(player)
	local box = Boxes.get(boxId :: string)
	if data == nil or box == nil or box.paid then
		return
	end
	local price = box.coins :: number
	local free = data.boxesOpened == 0 and box.id == FIRST_BOX
	if not free and SquishService.ownedCount(data) >= Economy.MaxOwned then
		Remotes.toast(player, "box.full")
		return
	end
	if not free and not SquishService.spendCoins(player, data, price, `box:{box.id}`) then
		Remotes.toast(player, "box.notEnough")
		return
	end
	grant(player, data, box, free)
end

--- The Robux box, called from the product grant. Ownership cap is not checked:
--- a paid purchase is always honoured, and the squish goes to the pocket.
function BoxService.grantPaid(player: Player, data: Types.ProfileData, boxId: string): boolean
	local box = Boxes.get(boxId)
	if box == nil or not box.paid then
		return false
	end
	return grant(player, data, box, false)
end

function BoxService.start()
	Remotes.event(Remotes.Names.OpenBox).OnServerEvent:Connect(onOpenBox)
end

return BoxService
