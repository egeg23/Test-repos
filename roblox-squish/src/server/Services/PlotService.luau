--!strict
--- Which base belongs to whom, and where things are in it.
---
--- Six bases are built once at server start. A joining player takes the first
--- free one and spawns on its home pad; a leaving player frees it, and their
--- shelves are cleared so the next owner walks into an empty base.

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Base = require(ReplicatedStorage.Shared.Config.Base)
local Builder = require(script.Parent.Parent.World.Builder)

local PlotService = {}

local plots: { Model } = {}
local owners: { [number]: Player } = {}
local plotOf: { [Player]: number } = {}

local claimedEvent = Instance.new("BindableEvent")
--- Fires (player, index) when a player takes a base.
PlotService.Claimed = claimedEvent.Event
local releasedEvent = Instance.new("BindableEvent")
--- Fires (player, index) after a player's base is freed.
PlotService.Released = releasedEvent.Event

function PlotService.plotIndex(player: Player): number?
	return plotOf[player]
end

function PlotService.owner(index: number): Player?
	return owners[index]
end

function PlotService.model(index: number): Model
	return plots[index]
end

function PlotService.slotCFrame(index: number, slot: number): CFrame
	local top = Base.slotTop(slot)
	-- Squishes face the door, which is +Z; a model's front is -Z, so turn it.
	return Builder.localToWorld(index, top[1], top[2], top[3]) * CFrame.Angles(0, math.pi, 0)
end

function PlotService.homeCFrame(index: number): CFrame
	local pad = Base.HomePad.centre
	return Builder.localToWorld(index, pad[1], pad[2], pad[3])
end

--- Local-frame coordinates of a world position in a plot.
function PlotService.toLocal(index: number, position: Vector3): (number, number)
	return Base.toLocal(index, position.X, position.Z)
end

--- The plot a world position is inside the walls of, if any.
function PlotService.plotAt(position: Vector3): number?
	for index = 1, Base.PlotCount do
		local x, z = PlotService.toLocal(index, position)
		if Base.insideWalls(x, z) then
			return index
		end
	end
	return nil
end

local function spawnAtHome(player: Player, character: Model)
	local index = plotOf[player]
	if index == nil then
		return
	end
	task.defer(function()
		if character.Parent ~= nil then
			character:PivotTo(PlotService.homeCFrame(index) + Vector3.new(0, 4, 0))
		end
	end)
end

local function claim(player: Player)
	for index = 1, Base.PlotCount do
		if owners[index] == nil then
			owners[index] = player
			plotOf[player] = index
			local model = plots[index]
			model:SetAttribute("OwnerUserId", player.UserId)
			model:SetAttribute("OwnerName", player.DisplayName)
			claimedEvent:Fire(player, index)
			player.CharacterAdded:Connect(function(character)
				spawnAtHome(player, character)
			end)
			if player.Character ~= nil then
				spawnAtHome(player, player.Character)
			end
			return
		end
	end
	-- The server is sized to the plot count, so this only happens if that is
	-- changed in one place and not the other.
	warn(`[squish] no free plot for {player.Name}`)
end

local function release(player: Player)
	local index = plotOf[player]
	if index == nil then
		return
	end
	plotOf[player] = nil
	owners[index] = nil
	local model = plots[index]
	model:SetAttribute("OwnerUserId", nil)
	model:SetAttribute("OwnerName", nil)
	for _, child in (model:FindFirstChild("Squishes") :: Folder):GetChildren() do
		child:Destroy()
	end
	for _, child in (model:FindFirstChild("Traps") :: Folder):GetChildren() do
		child:Destroy()
	end
	releasedEvent:Fire(player, index)
end

--- Called from the data service once a profile has loaded, so a player whose
--- data never arrives never holds a base.
function PlotService.claim(player: Player)
	if plotOf[player] == nil then
		claim(player)
	end
end

function PlotService.start()
	local folder = Instance.new("Folder")
	folder.Name = "Plots"
	folder.Parent = workspace
	Builder.buildPlaza(workspace)
	for index = 1, Base.PlotCount do
		plots[index] = Builder.buildPlot(index, folder)
	end
	-- Server size must equal the plot count. It cannot be set from a script;
	-- it is a Game Settings field, and the README says so.
	Players.PlayerRemoving:Connect(release)
end

return PlotService
