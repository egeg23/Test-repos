--!strict
local Strings = require("../src/shared/Strings")
local t = require("./harness")

local LOCALES = { "ru", "en", "es", "pt" }

return function()
	t.suite("Strings: coverage")

	t.test("every key exists in every launch locale", function()
		local missing: { string } = {}
		for key, bundle in Strings.Entries do
			for _, locale in LOCALES do
				local value = (bundle :: any)[locale]
				if typeof(value) ~= "string" or value == "" then
					table.insert(missing, `{key}/{locale}`)
				end
			end
		end
		if #missing > 0 then
			error(`{#missing} missing translation(s): {table.concat(missing, ", ")}`, 0)
		end
	end)

	t.test("placeholders survive translation", function()
		-- A translation that drops a {2} does not fail, it silently renders a
		-- sentence with a number missing from the middle of it. Comparing the
		-- placeholder sets is the only way that shows up before a player sees it.
		local broken: { string } = {}
		for key, bundle in Strings.Entries do
			local source = (bundle :: any).ru
			if typeof(source) ~= "string" then
				continue
			end
			local reference: { [string]: boolean } = {}
			for placeholder in string.gmatch(source, "{(%d+)}") do
				reference[placeholder] = true
			end

			for _, locale in LOCALES do
				local text = (bundle :: any)[locale]
				-- A locale that is missing outright is the coverage test's
				-- finding, not this one's. Without this guard that failure lands
				-- here as a Lua error about gmatch, which says nothing useful.
				if typeof(text) ~= "string" then
					continue
				end

				local seen: { [string]: boolean } = {}
				for placeholder in string.gmatch(text, "{(%d+)}") do
					seen[placeholder] = true
				end
				for placeholder in reference do
					if not seen[placeholder] then
						table.insert(broken, `{key}/{locale} is missing ` .. "{" .. placeholder .. "}")
					end
				end
				for placeholder in seen do
					if not reference[placeholder] then
						table.insert(broken, `{key}/{locale} has an extra placeholder`)
					end
				end
			end
		end
		if #broken > 0 then
			error(`{#broken} placeholder mismatch(es): {table.concat(broken, "; ")}`, 0)
		end
	end)

	t.suite("Strings: lookup")

	t.test("a plain string comes back as written", function()
		t.equal(Strings.get("common.close", "ru"), "Закрыть", "common.close in Russian")
		t.equal(Strings.get("common.close", "pt"), "Fechar", "common.close in Portuguese")
	end)

	t.test("placeholders are filled positionally", function()
		t.equal(Strings.get("base.slots", "en", 3, 6), "Shelves: 3 of 6", "filled")
	end)

	t.test("an unknown key returns itself rather than nothing", function()
		-- A visible key on screen is a bug report; a blank space is a mystery.
		t.equal(Strings.get("base.doesNotExist", "ru"), "base.doesNotExist", "unknown key")
	end)

	t.test("an unknown locale falls back rather than blanking", function()
		t.equal(Strings.get("common.close", "de"), "Close", "German falls back to English")
	end)

	t.test("an unpassed placeholder stays visible", function()
		local text = Strings.get("base.slots", "en", 3)
		t.isTrue(string.find(text, "{2}") ~= nil, "missing argument is left in place")
	end)

	t.test("the game's name is defined once, in every locale", function()
		local name = Strings.Entries["brand.name"]
		t.isTrue(name ~= nil, "brand.name exists")
	end)

	t.test("every squish, rarity, box, trap and paid item has a name", function()
		local Squishes = require("../src/shared/Config/Squishes")
		local Boxes = require("../src/shared/Config/Boxes")
		local Traps = require("../src/shared/Config/Traps")
		local Monetization = require("../src/shared/Config/Monetization")
		local missing: { string } = {}
		local function need(key: string)
			if Strings.Entries[key] == nil then
				table.insert(missing, key)
			end
		end
		for _, species in Squishes.List do
			need(`squish.{species.id}`)
		end
		for _, rarity in Squishes.RarityOrder do
			need(`rarity.{rarity}`)
		end
		for _, box in Boxes.List do
			need(`box.{box.id}`)
		end
		for _, trap in Traps.List do
			need(`trap.{trap.id}`)
			need(`trap.{trap.id}.desc`)
		end
		for _, pass in Monetization.Passes do
			need(`pass.{pass.id}`)
			need(`pass.{pass.id}.desc`)
		end
		for _, product in Monetization.Products do
			need(`product.{product.id}`)
			need(`product.{product.id}.desc`)
		end
		for _, reward in Monetization.AdRewards do
			need(`ad.{reward.id}`)
		end
		if #missing > 0 then
			error(`no string for: {table.concat(missing, ", ")}`, 0)
		end
	end)

	t.suite("Strings: content")

	t.test("no translation is left as the Russian original", function()
		-- The commonest way a translation pass goes wrong is a copy-paste that
		-- never got translated. Identical strings across languages are sometimes
		-- correct -- "Mochi", "Boba" -- so only long strings are counted.
		local suspicious = 0
		for _, bundle in Strings.Entries do
			local ru = (bundle :: any).ru
			if (bundle :: any).en == ru and #ru > 12 then
				suspicious += 1
			end
		end
		t.equal(suspicious, 0, "long strings identical in Russian and English")
	end)
end
