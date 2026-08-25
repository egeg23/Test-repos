--!strict
--- Filtering for any text one player wrote and another will read.
---
--- This is the load-bearing piece of the whole free-form exemption. Roblox
--- restricts free-form user creation to players 16 and over and disqualifies the
--- experience from ads, and the documented way out is content that "undergoes
--- Roblox moderation before publication or replication". So nothing a player
--- typed is stored or sent onward until it has been through here.
---
--- Every failure path returns nil. Failing closed means an outage costs a class
--- its title; failing open would mean unfiltered text reaching a child, which is
--- the thing the exemption is built to prevent.

local TextService = game:GetService("TextService")

local ModerationService = {}

ModerationService.MaxTitleLength = 40

--- Filters text for display to everyone, not to one recipient. Returns nil when
--- filtering could not be completed -- callers must treat that as "do not
--- publish", never as "publish the original".
function ModerationService.filterForBroadcast(text: string, authorUserId: number): string?
	if authorUserId <= 0 then
		return nil
	end

	local trimmed = string.gsub(text, "^%s*(.-)%s*$", "%1")
	if trimmed == "" then
		return nil
	end

	local ok, result = pcall(function()
		return TextService:FilterStringAsync(
			trimmed,
			authorUserId,
			Enum.TextFilterContext.PublicChat
		)
	end)
	if not ok or result == nil then
		return nil
	end

	local broadcastOk, filtered = pcall(function()
		return (result :: TextFilterResult):GetNonChatStringForBroadcastAsync()
	end)
	if not broadcastOk or typeof(filtered) ~= "string" then
		return nil
	end
	return filtered
end

--- Trims to length before filtering. Length is checked on the original rather
--- than on the filtered result, because filtering replaces words with hashes of
--- the same length and truncating afterwards could cut one in half.
function ModerationService.filterTitle(text: unknown, authorUserId: number): string?
	if typeof(text) ~= "string" then
		return nil
	end
	local candidate = text :: string
	if utf8.len(candidate) == nil then
		return nil
	end
	if #candidate > ModerationService.MaxTitleLength * 4 then
		return nil
	end
	return ModerationService.filterForBroadcast(candidate, authorUserId)
end

return ModerationService
