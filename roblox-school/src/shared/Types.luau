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
	--- User id (as a string, because DataStore serialises through JSON) -> the
	--- unix second that member was last seen active in this class.
	---
	--- A list of ids would grow and never shrink: a student who joins and stops
	--- playing stays counted forever, and the member count is the fill rate,
	--- which is what the teacher is paid on. Timestamps let a class forget people
	--- who left without saying so.
	members: { [string]: number },
	--- The student appointed monitor of this class, or 0 for none. One per class:
	--- the point of the role is that it is a distinction, and a class of twenty
	--- monitors is a class of none.
	monitorUserId: number,
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
	--- Whether the owner held the listing-priority pass when this class was
	--- created or last edited. Stored on the class rather than checked at listing
	--- time because the directory is read cross-server, where the owner is
	--- usually not present to have their passes read.
	listingPriority: boolean,
	updatedAt: number,
}

--- One student's verdict on a class, kept so a rating can be changed rather than
--- stacked, and so the same account cannot rate a class twenty times.
export type ClassRating = {
	classId: string,
	stars: number,
}

--- What this profile is, as stored.
---
--- Dean and director are deliberately absent: those are held by CampusService
--- per locale and per subject, and a copy on the profile would be a second truth
--- that goes stale the moment a term ends. This field carries only what belongs
--- to the player themselves.
export type Role = "student" | "monitor" | "teacher"

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
	playSeconds: number,
	points: number,
	grade: number,
	--- Lessons passed since entering the current grade. Reset on advance, so the
	--- grade requirement can grow without rewriting history.
	lessonsThisGrade: number,
	graduatedCount: number,
	--- University year, 0 for a school student. Set by choosing the university
	--- path at graduation; raises the pass mark, the lesson requirement and the
	--- reward together.
	tier: number,
	--- Lessons passed inside the current university year, counted apart from
	--- lessonsThisGrade so leaving university does not carry a part-finished year
	--- back into school.
	lessonsThisTier: number,
	--- The class this player is currently a monitor of, if any. Held here as well
	--- as on the class so a monitor's bonus can be read without loading a class
	--- the player may not even be enrolled in any more.
	monitorClassId: string?,
	--- Set when the last grade is finished and cleared once the player picks what
	--- to do next. Graduation is a branch the player chooses, not an event that
	--- happens to them.
	awaitingGraduation: boolean,
	subjects: { [string]: SubjectProgress },
	--- Monotonic counters the achievement branches are keyed to. Only ever
	--- incremented: a branch whose stat could fall would revoke a tier the player
	--- already saw granted, which is the one thing a progression system must
	--- never do.
	stats: { [string]: number },
	--- Achievement tier ids already granted, as `branch:index`. Ids rather than a
	--- per-branch count, because a count cannot say which tiers were granted once
	--- the thresholds are retuned -- and they will be.
	achievements: { [string]: boolean },
	--- Consecutive days with a session. `streakDay` is the day number the streak
	--- was last credited on, so a second session the same day does not extend it
	--- and a gap of one day does not silently keep it alive.
	streak: number,
	streakDay: number,
	--- What today's streak bonus paid, kept so the ad that doubles it knows the
	--- amount. Zeroed once doubled, which is also what stops it being doubled
	--- twice.
	streakReward: number,
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
	--- Lessons finished today, and the day that count belongs to. Feeds the
	--- diminishing-returns curve the lessonSlots pass raises the start of.
	lessonsToday: number,
	lessonDayStamp: number,
	--- Lesson stat key -> the unix second it was last failed. A failed lesson is
	--- closed to that student for a few minutes: enough that failing costs
	--- something, not enough to end a session.
	retryCooldowns: { [string]: number },
	--- Unix second this profile was last released. Offline notes accrue from it.
	lastSeenAt: number,
	--- The week number the weekly baselines were taken in, and what each ranked
	--- stat read at that moment. The weekly board score is the difference from
	--- these, so the lifetime counters stay the single source and there is no
	--- second set to keep in step.
	weeklyWeek: number,
	weeklyBaselines: { [string]: number },
}

return Types
