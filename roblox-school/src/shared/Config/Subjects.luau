--!strict
--- The eight subjects, their translation class and how they are played.

local Types = require(script.Parent.Parent.Types)

local Subjects = {}

export type Entry = {
	id: string,
	kind: Types.SubjectKind,
	--- Lesson kinds a teacher may author for this subject. The first is the default.
	lessonKinds: { Types.LessonKind },
	displayKey: string,
}

--- `universal` subjects are authored once and machine-translated into every
--- locale, so a pool written by Russian teachers serves Brazilian students. The
--- content pool compounds globally instead of fragmenting per language.
---
--- `localeBound` subjects are authored separately per locale and never
--- translated. The obstacle is not vocabulary, it is that the canon differs: a
--- perfectly translated question about the Russian literature syllabus is still
--- the wrong question for an American twelve-year-old.
Subjects.List = {
	{ id = "math", kind = "universal", lessonKinds = { "quiz" }, displayKey = "subject.math" },
	{
		id = "science",
		kind = "universal",
		lessonKinds = { "quiz", "assembly" },
		displayKey = "subject.science",
	},
	{ id = "logic", kind = "universal", lessonKinds = { "quiz" }, displayKey = "subject.logic" },
	{ id = "pe", kind = "universal", lessonKinds = { "obstacle" }, displayKey = "subject.pe" },
	{ id = "art", kind = "universal", lessonKinds = { "assembly" }, displayKey = "subject.art" },
	{
		id = "literature",
		kind = "localeBound",
		lessonKinds = { "quiz", "ordering" },
		displayKey = "subject.literature",
	},
	{
		id = "history",
		kind = "localeBound",
		lessonKinds = { "quiz", "ordering" },
		displayKey = "subject.history",
	},
	{
		id = "language",
		kind = "localeBound",
		lessonKinds = { "quiz" },
		displayKey = "subject.language",
	},
} :: { Entry }

local byId: { [string]: Entry } = {}
for _, entry in Subjects.List do
	byId[entry.id] = entry
end

function Subjects.get(id: string): Entry?
	return byId[id]
end

--- Whether a lesson in this subject may be machine-translated for other locales.
function Subjects.isTranslatable(id: string): boolean
	local entry = byId[id]
	return entry ~= nil and entry.kind == "universal"
end

function Subjects.allows(id: string, kind: Types.LessonKind): boolean
	local entry = byId[id]
	if entry == nil then
		return false
	end
	for _, allowed in entry.lessonKinds do
		if allowed == kind then
			return true
		end
	end
	return false
end

return Subjects
