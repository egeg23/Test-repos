--!strict
--- Machine translation for content that survives it.
---
--- Only universal subjects go through here. A maths question is the same question
--- in Portuguese; a question about the Russian literature syllabus translates
--- into a grammatical sentence and a useless question, so locale-bound subjects
--- are never touched.
---
--- The API is reached through the Open Cloud SDK, which authenticates as the
--- server rather than with a key, and which is not part of this repository -- it
--- is added to ServerScriptService from Roblox's package. Everything here is
--- written so that its absence is a normal state: no translations, content stays
--- in the language it was written in, nothing breaks. The API is also documented
--- as early development and untestable in Studio, which is the other reason not
--- to build anything load-bearing on top of it.

local ReplicatedStorage = game:GetService("ReplicatedStorage")
local ServerScriptService = game:GetService("ServerScriptService")

local Locales = require(ReplicatedStorage.Shared.Config.Locales)
local Subjects = require(ReplicatedStorage.Shared.Config.Subjects)
local ModerationService = require(script.Parent.ModerationService)

local TranslationService = {}

local sdk: any = nil
local sdkChecked = false

local function getSdk(): any
	if sdkChecked then
		return sdk
	end
	sdkChecked = true

	local container = ServerScriptService:FindFirstChild("OpenCloud")
	if container == nil then
		return nil
	end
	local versioned = container:FindFirstChild("V2")
	if versioned == nil or not versioned:IsA("ModuleScript") then
		return nil
	end

	local ok, loaded = pcall(require, versioned)
	if ok and typeof(loaded) == "table" then
		sdk = loaded
	end
	return sdk
end

function TranslationService.isAvailable(): boolean
	return getSdk() ~= nil
end

--- Every launch locale except the one the text is already in.
local function targetsFor(sourceLocale: string): { string }
	local targets: { string } = {}
	for _, entry in Locales.List do
		if entry.id ~= sourceLocale then
			table.insert(targets, entry.id)
		end
	end
	return targets
end

--- One field into every target locale. Returns an empty map on any failure,
--- which callers treat as "no translation" rather than as an error.
local function translateField(text: string, sourceLocale: string): { [string]: string }
	local api = getSdk()
	if api == nil then
		return {}
	end

	local ok, response = pcall(function()
		return api:TranslateText({
			path = api:UniversePath(game.GameId),
			text = text,
			source_language_code = sourceLocale,
			target_language_codes = targetsFor(sourceLocale),
		})
	end)

	if not ok or typeof(response) ~= "table" then
		return {}
	end
	local translations = (response :: any).translations
	if typeof(translations) ~= "table" then
		-- The API returns an empty map when the source text was filtered out.
		return {}
	end

	local result: { [string]: string } = {}
	for locale, value in translations :: { [string]: any } do
		if typeof(value) == "string" and value ~= "" then
			result[locale] = value
		end
	end
	return result
end

export type TranslatedQuestion = {
	stem: string,
	options: { string },
	explanation: string,
}

--- Translates a question into every other launch locale.
---
--- Machine output is filtered again before it is stored. Translation can produce
--- something the source filter had no reason to catch, and the entire free-form
--- exemption rests on nothing unmoderated reaching a player -- which includes
--- text this game generated on their behalf.
function TranslationService.translateQuestion(
	subject: string,
	sourceLocale: string,
	authorUserId: number,
	stem: string,
	options: { string },
	explanation: string
): { [string]: TranslatedQuestion }
	if not Subjects.isTranslatable(subject) or getSdk() == nil then
		return {}
	end

	local stems = translateField(stem, sourceLocale)
	local explanations = translateField(explanation, sourceLocale)
	local optionSets: { { [string]: string } } = {}
	for _, option in options do
		table.insert(optionSets, translateField(option, sourceLocale))
	end

	local result: { [string]: TranslatedQuestion } = {}
	for _, locale in targetsFor(sourceLocale) do
		local translatedStem = stems[locale]
		local translatedExplanation = explanations[locale]
		if translatedStem == nil or translatedExplanation == nil then
			continue
		end

		local translatedOptions: { string } = {}
		local complete = true
		for _, set in optionSets do
			local value = set[locale]
			if value == nil then
				complete = false
				break
			end
			table.insert(translatedOptions, value)
		end
		-- A question missing one translated option is not a partly translated
		-- question, it is a broken one.
		if not complete then
			continue
		end

		local safeStem = ModerationService.filterForBroadcast(translatedStem, authorUserId)
		local safeExplanation =
			ModerationService.filterForBroadcast(translatedExplanation, authorUserId)
		if safeStem == nil or safeExplanation == nil then
			continue
		end

		local safeOptions: { string } = {}
		local optionsClean = true
		for _, option in translatedOptions do
			local safe = ModerationService.filterForBroadcast(option, authorUserId)
			if safe == nil then
				optionsClean = false
				break
			end
			table.insert(safeOptions, safe)
		end
		if not optionsClean then
			continue
		end

		result[locale] = {
			stem = safeStem,
			options = safeOptions,
			explanation = safeExplanation,
		}
	end

	return result
end

return TranslationService
