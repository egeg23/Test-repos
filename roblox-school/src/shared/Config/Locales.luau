--!strict
--- Launch locales.
---
--- The experience is never split per language. Ad eligibility needs 2,000 unique
--- visitors per month *per experience*, so a 6,000-MAU game cut into four
--- language builds becomes four ineligible 1,500-MAU games -- and splits the
--- return-rate signal discovery actually ranks on. Language is handled by
--- matchmaking weight and a per-class tag instead.

local Types = require(script.Parent.Parent.Types)

local Locales = {}

export type Entry = {
	id: Types.LocaleId,
	--- IETF tags that map onto this locale. Player.LocaleId is matched by prefix.
	localePrefixes: { string },
	displayName: string,
}

Locales.List = {
	{ id = "ru", localePrefixes = { "ru" }, displayName = "Русский" },
	{ id = "en", localePrefixes = { "en" }, displayName = "English" },
	{ id = "es", localePrefixes = { "es" }, displayName = "Español" },
	{ id = "pt", localePrefixes = { "pt" }, displayName = "Português" },
} :: { Entry }

Locales.Default = "en" :: Types.LocaleId

--- Resolves a Roblox Player.LocaleId ("ru-ru", "pt-br", ...) onto a launch locale.
--- Unknown locales fall back to English rather than being rejected: a player we
--- have no content for should still see a full school, just not in their language.
function Locales.fromPlayerLocaleId(localeId: string): Types.LocaleId
	local lowered = string.lower(localeId)
	for _, entry in Locales.List do
		for _, prefix in entry.localePrefixes do
			if string.sub(lowered, 1, #prefix) == prefix then
				return entry.id
			end
		end
	end
	return Locales.Default
end

function Locales.isSupported(id: string): boolean
	for _, entry in Locales.List do
		if entry.id == id then
			return true
		end
	end
	return false
end

return Locales
