--!strict
--- Shared type definitions.
---
--- Nothing here has behaviour; it exists so server and client agree on the shape
--- of a lesson, a class and a profile without importing each other.

local Types = {}

export type LocaleId = "ru" | "en" | "es" | "pt"

--- Universal subjects are numbers, formulas and movement: they survive machine
--- translation, so one pool serves every locale. Locale-bound subjects differ by
--- canon rather than by wording -- translating a question about Onegin into
--- English produces a correct sentence and a useless question -- so they are
--- authored per locale and never translated.
export type SubjectKind = "universal" | "localeBound"

--- How a lesson is played. Half the subjects are not quizzes: assembling a
--- circuit from prefab blocks or running a teacher-built obstacle course teaches
--- better, and (being assembly from 3D assets) is exempt from the free-form
--- user creation rules that govern authored text.
export type LessonKind = "quiz" | "obstacle" | "assembly" | "ordering"

export type Question = {
	id: string,
	subject: string,
	grade: number,
	stem: string,
	options: { string },
	--- 1-based index into `options`.
	answer: number,
	--- Shown after the player answers, right or wrong. The whole educational
	--- claim of the game rests on this field, not on the question.
	explanation: string,
}

export type TestSpec = {
	id: string,
	subject: string,
	grade: number,
	--- Questions drawn per attempt out of `poolIds`. Drawing a subset from a much
	--- larger pool is what makes leaked answer lists worth little.
	draw: number,
	poolIds: { string },
	timeLimitSeconds: number?,
	--- Fraction of drawn questions needed to pass, 0..1.
	passFraction: number,
}

export type ObstacleSpec = {
	id: string,
	--- Prefab module ids in run order.
	moduleIds: { string },
	--- Target grade. Every dimension of the course -- gap width, beam width, how
	--- long a tile lasts, whether there are checkpoints at all -- is derived from
	--- this one number, which is why a teacher choosing it is choosing the whole
	--- difficulty of the course.
	grade: number,
}

export type AssemblySpec = {
	id: string,
	--- Ids into the curated assembly catalogue. A lesson picks which tasks to
	--- set, never what the right answer to one is.
	taskIds: { string },
}

export type ModerationStatus = "draft" | "pending" | "published" | "rejected"


export type Lesson = {
	id: string,
	authorUserId: number,
	subject: string,
	grade: number,
	kind: LessonKind,
	locale: LocaleId,
	title: string,
	body: string,
	status: ModerationStatus,
	--- Locale id -> translated body, populated only for universal subjects and
	--- only after the translation has itself been filtered.
	translations: { [string]: string },
	test: TestSpec?,
	obstacle: ObstacleSpec?,
	assembly: AssemblySpec?,
	createdAt: number,
	publishedAt: number?,
}

export type Class = {
	id: string,
	teacherUserId: number,
	teacherName: string,
	locale: LocaleId,
	subject: string,
	title: string,
	--- The school year this class teaches. Sets the window a teacher may pick an
	--- obstacle course difficulty inside, and tells students whether the class is
	--- meant for them.
	grade: number,
	capacity: number,
	memberUserIds: { number },
	--- Lessons are embedded rather than stored separately: a class holds a
	--- handful of them, they are always read together with it, and one read per
	--- lesson start beats two.
	lessons: { [string]: Lesson },
	rating: number,
	ratingCount: number,
	--- Unix seconds until which this class is promoted in the directory. Lives on
	--- the class, not on the teacher's profile, because the promotion has to keep
	--- working while the teacher is offline -- which is the normal case.
	promoUntil: number,
	createdAt: number,
	updatedAt: number,
}

--- One student's verdict on a class, kept so a rating can be changed rather than
--- stacked, and so the same account cannot rate a class twenty times.
export type ClassRating = {
	classId: string,
	stars: number,
}

export type Role = "student" | "monitor" | "teacher" | "dean" | "director"

export type TeacherRank = "assistant" | "docent" | "professor"

export type SubjectProgress = {
	xp: number,
	lessonsPassed: number,
}

--- Keys that hold a user id are strings, not numbers: DataStore serialises through
--- JSON, which has no integer keys, so a numeric key silently comes back as a
--- string and every lookup misses.
export type TeacherState = {
	licensed: boolean,
	rank: TeacherRank,
	rating: number,
	ratingCount: number,
	classIds: { string },
	--- Points earned from teaching that have not yet been moved into `points`.
	pendingPayout: number,
}

--- What this player owes a given teacher's decay curve, keyed by teacher user id.
---
--- These counters live on the *student* rather than the teacher because lessons
--- are asynchronous: the teacher is usually offline when their lesson is taken,
--- so their profile is not available to read a decay factor out of. The student
--- is by definition present. The pair is symmetric, so either side can hold it.
export type TeacherHistoryEntry = {
	completions: number,
	paid: number,
}

export type ProfileData = {
	schemaVersion: number,
	locale: LocaleId,
	createdAt: number,
	playSeconds: number,
	points: number,
	grade: number,
	--- Lessons passed since entering the current grade. Reset on advance, so the
	--- grade requirement can grow without rewriting history.
	lessonsThisGrade: number,
	graduatedCount: number,
	--- Set when the last grade is finished and cleared once the player picks what
	--- to do next. Graduation is a branch the player chooses, not an event that
	--- happens to them.
	awaitingGraduation: boolean,
	subjects: { [string]: SubjectProgress },
	achievements: { [string]: boolean },
	role: Role,
	--- The class this student is currently enrolled in, if any. One at a time:
	--- being in six classes at once would make the fill-rate factor meaningless.
	enrolledClassId: string?,
	--- Class id -> stars this player gave it. Kept so a rating can be revised
	--- instead of stacked, and so one account cannot rate a class twenty times.
	classRatings: { [string]: number },
	teacher: TeacherState,
	teacherHistory: { [string]: TeacherHistoryEntry },
	--- Receipt ids already granted, mapped to when. Makes ProcessReceipt
	--- idempotent across the retries Roblox performs when a grant is not
	--- acknowledged.
	grantedReceipts: { [string]: number },
	--- Ad reward id -> unix seconds of the last successful view.
	adCooldowns: { [string]: number },
	--- Ad reward id -> views taken during `adDayStamp`.
	adDailyCounts: { [string]: number },
	adDayStamp: number,
	ownedPasses: { [string]: boolean },
	--- Boost id -> unix seconds at which it expires.
	activeBoosts: { [string]: number },
	--- Consumable id -> remaining count. Separate from activeBoosts because a
	--- spare test attempt is a charge to spend, not a window that runs out.
	consumables: { [string]: number },
}

return Types
