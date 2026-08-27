--!strict
--- Points that accrue while a student is away, for holders of the notes pass.
---
--- This exists because the pass was already on sale. "Auto-conspectus" was
--- listed, purchasable and granted, and nothing anywhere read it -- one of six
--- passes in that state. A pass that sells nothing is worse than a missing
--- feature: the player paid.
---
--- The design constraint is narrow. Offline income has to be worth coming back
--- for and must never be worth *not* playing for, so it is small per minute and
--- capped at eight hours: a night away collects in full, a fortnight away
--- collects the same as a night. Nobody optimises by staying logged out.

local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Limits = require(ReplicatedStorage.Shared.Config.Limits)
local Remotes = require(ReplicatedStorage.Shared.Remotes)
local Analytics = require(script.Parent.AnalyticsService)
local DataService = require(script.Parent.DataService)
local PurchaseService = require(script.Parent.PurchaseService)

local OfflineNotesService = {}

--- Credits whatever accrued since this profile was last released.
---
--- Returns what was paid, so a caller can tell the player. Zero for a player
--- without the pass, a first session, or an absence too short to bother naming.
function OfflineNotesService.collect(player: Player): number
	local data = DataService.getData(player)
	if data == nil then
		return 0
	end

	local since = data.lastSeenAt
	-- Consumed whatever happens, before any decision to pay. A stamp left in
	-- place would pay the same absence again on the next join.
	data.lastSeenAt = os.time()

	if since <= 0 then
		return 0
	end
	if not PurchaseService.ownsPass(player, "autoNotes") then
		return 0
	end

	-- The doubling charge is spent only when there is something to double.
	local doubled = (data.consumables.offlineX2 or 0) > 0
	local amount = Limits.offlineNotes(os.time() - since, doubled)
	if amount < Limits.MinOfflineNotesToReport then
		return 0
	end
	if doubled then
		data.consumables.offlineX2 -= 1
	end

	data.points += amount
	Analytics.pointsEarned(player, amount, data.points, "offlineNotes")
	Remotes.event(Remotes.Names.OfflineNotes):FireClient(player, {
		points = amount,
		awaySeconds = os.time() - since,
		doubled = doubled,
	})
	return amount
end

function OfflineNotesService.start()
	DataService.ProfileLoaded:Connect(function(player: Player)
		-- Spawned rather than called inline: ownsPass can be a web request, and
		-- profile-loaded handlers run in a chain that should not wait on one.
		task.spawn(OfflineNotesService.collect, player)
	end)
end

return OfflineNotesService
