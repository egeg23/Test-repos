--!strict
--- Shapes shared by server, client and the tests.
---
--- Nothing in here touches the engine, so the config and logic modules that
--- import it can run under the standalone Luau binary.

local Types = {}

export type LocaleId = "ru" | "en" | "es" | "pt"

export type Rarity = "common" | "rare" | "epic" | "legendary" | "mythic"

--- Where a squish came from. Kept on the record because the show and the
--- analytics both care, and because "came from a theft" is what the return-home
--- roll and the trade cooldown key off.
export type Origin = "starter" | "box" | "merge" | "stolen" | "trade" | "show"

--- One squish a player owns. Species and tier are the whole identity for
--- merging; the uid exists so two identical squishes are still two things.
export type Squish = {
	uid: string,
	species: string,
	tier: number,
	origin: Origin,
	obtainedAt: number,
	--- Bought with Robux, directly or by merging with something that was. It
	--- follows the squish through merges and trades, because Roblox's paid item
	--- trading rule is about the item, not about who holds it now.
	paid: boolean?,
}

export type ProfileData = {
	schemaVersion: number,
	locale: LocaleId,
	--- Server-accumulated, never client-reported. Newbie protection and the
	--- trade gate both read it.
	playSeconds: number,
	coins: number,
	totalEarned: number,
	nextUid: number,
	--- Every squish owned, by uid.
	squishes: { [string]: Squish },
	--- Slot number (as a string, so the DataStore never sees a sparse array) to
	--- uid. A squish that is owned but not on a shelf sits in the pocket: safe
	--- from thieves, earning nothing.
	shelves: { [string]: string },
	--- Slots bought with coins, on top of the starting count.
	boughtSlots: number,
	traps: { [string]: number },
	--- Boxes opened per box type since the last pity-qualifying result.
	pity: { [string]: number },
	boxesOpened: number,
	starterGiven: boolean,
	stats: { [string]: number },
	--- Theft bookkeeping. lossDay rolls lossesToday over at UTC midnight.
	lossesToday: number,
	lossDay: number,
	shieldUntil: number,
	--- A newbie who steals gives up the rest of their protection: protection
	--- that works only in one direction would be a free head start at theft.
	forfeitedProtection: boolean,
	showWeekClaimed: number,
	onboardingDone: boolean,
	lastTradeAt: number,
	grantedReceipts: { [string]: number },
	adCooldowns: { [string]: number },
	adDailyCounts: { [string]: number },
	adDayStamp: number,
	ownedPasses: { [string]: boolean },
	activeBoosts: { [string]: number },
}

return Types
