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
	modules: { string },
	difficulty: number,
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
	createdAt: number,
	publishedAt: number?,
}

export type Class = {
	id: string,
	teacherUserId: number,
	locale: LocaleId,
	subject: string,
	title: string,
	capacity: number,
	memberUserIds: { number },
	lessonIds: { string },
	rating: number,
	ratingCount: number,
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
	--- Lifetime payout already drawn from each student. Caps a teacher farming a
	--- small circle of friends indefinitely.
	studentPayouts: { [string]: number },
	--- Completions per student, driving uniqueness decay.
	studentCompletions: { [string]: number },
}

export type ProfileData = {
	schemaVersion: number,
	locale: LocaleId,
	createdAt: number,
	playSeconds: number,
	points: number,
	grade: number,
	graduatedCount: number,
	subjects: { [string]: SubjectProgress },
	achievements: { [string]: boolean },
	role: Role,
	teacher: TeacherState,
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
