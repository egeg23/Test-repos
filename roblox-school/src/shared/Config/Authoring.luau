--!strict
--- The rules a question has to satisfy, whoever wrote it.
---
--- These govern the curated bank and a teacher's own questions equally. That is
--- the point of the file: a rule that applies to our content and not to theirs is
--- a rule players will find and walk through. tools/validate_bank.py parses these
--- constants rather than keeping its own copy, so the bank and the game cannot
--- disagree about what a good question looks like.

local Authoring = {}

Authoring.MaxStemChars = 120
Authoring.MinStemChars = 8
Authoring.RequiredOptions = 4
Authoring.MaxOptionChars = 60
Authoring.MinExplanationChars = 20
Authoring.MaxExplanationChars = 240

--- An option this much longer than the average reads as the answer on sight.
Authoring.MaxOptionLengthRatio = 1.8

Authoring.MinGrade = 1
Authoring.MaxGrade = 11

--- Roblox's rewarded-video eligibility list requires that an experience "offer no
--- free-form user creation". The content-maturity documentation exempts "anything
--- that goes through Roblox moderation before it's published or replicated" --
--- which is exactly what AuthoringService does -- but the Maturity & Compliance
--- questionnaire repeats only the 3D-assembly half of that exemption, and no
--- Roblox staff answer confirms the moderation half in writing.
---
--- So this switch decides which side of an unconfirmed bet the build is on:
---   true  -- teachers may write their own questions. Full design, ad eligibility
---            rests on the moderation exemption holding.
---   false -- bank picks and prefab assembly only. Nothing a player typed ever
---            reaches another player, so the questionnaire answer is "no" with
---            nothing to argue about.
--- Flipping it to false must not break anything: prefab courses, assembly tasks
--- and the whole bank stay available, and a teacher's income formula does not
--- reference authored questions.
Authoring.FreeTextEnabled = true

--- How many questions one teacher may have live at once. A cap on volume is
--- also a cap on how much damage one bad actor can do before a dean notices.
Authoring.MaxAuthoredPerTeacher = 60

export type Draft = {
	subject: string,
	grade: number,
	stem: string,
	options: { string },
	answer: number,
	explanation: string,
}

export type Result = { ok: boolean, reason: string? }

--- Structural checks only. Whether the text is *acceptable* is TextService's
--- job, and whether it is *true* is nobody's job here -- that is what the pass
--- rate and the dean are for.
function Authoring.validate(draft: Draft): Result
	local stemLength = utf8.len(draft.stem)
	if stemLength == nil then
		return { ok = false, reason = "badEncoding" }
	end
	if stemLength < Authoring.MinStemChars then
		return { ok = false, reason = "stemTooShort" }
	end
	if stemLength > Authoring.MaxStemChars then
		return { ok = false, reason = "stemTooLong" }
	end

	if #draft.options ~= Authoring.RequiredOptions then
		return { ok = false, reason = "optionCount" }
	end
	if draft.answer < 1 or draft.answer > Authoring.RequiredOptions then
		return { ok = false, reason = "badAnswer" }
	end

	local seen: { [string]: boolean } = {}
	local total = 0
	local longest = 0
	for _, option in draft.options do
		local length = utf8.len(option)
		if length == nil or length == 0 then
			return { ok = false, reason = "emptyOption" }
		end
		if length > Authoring.MaxOptionChars then
			return { ok = false, reason = "optionTooLong" }
		end
		local key = string.lower(option)
		if seen[key] then
			return { ok = false, reason = "duplicateOption" }
		end
		seen[key] = true
		total += length
		longest = math.max(longest, length)
	end

	local mean = total / Authoring.RequiredOptions
	if mean > 0 and longest / mean > Authoring.MaxOptionLengthRatio then
		return { ok = false, reason = "lopsidedOptions" }
	end

	local explanationLength = utf8.len(draft.explanation)
	if explanationLength == nil then
		return { ok = false, reason = "badEncoding" }
	end
	-- The explanation is where the learning happens. A question without one is a
	-- quiz item; with one it is a lesson.
	if explanationLength < Authoring.MinExplanationChars then
		return { ok = false, reason = "explanationTooShort" }
	end
	if explanationLength > Authoring.MaxExplanationChars then
		return { ok = false, reason = "explanationTooLong" }
	end

	if draft.grade < Authoring.MinGrade or draft.grade > Authoring.MaxGrade then
		return { ok = false, reason = "badGrade" }
	end

	return { ok = true, reason = nil }
end

return Authoring
