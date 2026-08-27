--!strict
--- The player's language, resolved once and kept current.
---
--- Resolved on the client from Player.LocaleId through the same shared table the
--- server uses, so both sides land on the same launch locale for the same player
--- rather than each deciding for themselves.
---
--- LocaleId can change mid-session -- a player switching language in the Roblox
--- app -- so it is watched rather than read once and cached forever.

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Locales = require(ReplicatedStorage.Shared.Config.Locales)
local Strings = require(ReplicatedStorage.Shared.Strings)

local Locale = {}

local player = Players.LocalPlayer
local current = Locales.fromPlayerLocaleId(player.LocaleId)

local changed = Instance.new("BindableEvent")

--- Fires when the player switches language. Panels rebuilt on open pick the new
--- language up on their own; anything long-lived listens to this.
Locale.Changed = changed.Event

player:GetPropertyChangedSignal("LocaleId"):Connect(function()
	local resolved = Locales.fromPlayerLocaleId(player.LocaleId)
	if resolved ~= current then
		current = resolved
		changed:Fire(resolved)
	end
end)

function Locale.id(): string
	return current
end

--- Shorthand for the lookup, since it appears on nearly every line of interface
--- code: `L.text("class.join")`.
function Locale.text(key: string, ...): string
	return Strings.get(key, current, ...)
end

return Locale
