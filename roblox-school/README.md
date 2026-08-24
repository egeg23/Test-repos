# roblox-school

A Roblox experience where players teach players. Students take lessons, players
who graduate can become teachers, teachers build classes and earn from how well
their students actually do, and each language community elects its own school
leadership every month.

Monetization runs on two lanes: buy the advantage, or watch ads and close most of
the gap. How much of the gap stays open is one tunable constant,
`Economy.AdCatchUpTarget`, and `tools/simulate_economy.py` checks the game
actually delivers it.

## Why the code is shaped this way

Two platform rules drove nearly every structural decision, so they are worth
knowing before reading the source.

**Free-form user creation.** Roblox defines it as letting players "create
anything within an experience, such as writing words or making illustrations on a
chalkboard" — a school chalkboard is their own example. An experience that offers
it is restricted to players 16 and over and is disqualified from ads. The
documented exemption is content that "undergoes Roblox moderation before
publication or replication", so:

- authored text never reaches another player without passing `TextService`
  filtering and a publication queue;
- assembly from prefabs — obstacle courses, circuit builds, compositions — is
  explicitly *not* free-form, so those publish immediately and give teachers a
  creative outlet with no moderation latency at all.

**Ad eligibility is per experience.** It needs 2,000 unique monthly visitors, so a
6,000-MAU game split into four language builds becomes four ineligible
1,500-MAU games. The experience is therefore never split by language. Instead
language is a weighted matchmaking attribute (servers self-sort) plus a hard tag
on each class (`Player.LocaleId` picks the default filter, and the player can
override it — someone learning English *wants* the English class).

Universal subjects — maths, science, logic, PE, art — are authored once and
machine-translated, so a pool written by Russian teachers serves Brazilian
students. Locale-bound subjects — literature, history, native language — are
authored per locale and never translated, because the obstacle there is not
vocabulary but that the canon differs.

## Layout

```
src/shared/     types, and config for locales, subjects, progression,
                economy and monetization
src/server/     services: data, purchases, ads, rate limiting
src/client/     controllers
content/banks/  seed question banks, per locale
tools/          checks that run outside Studio
```

## Running the checks

```sh
./tools/check_all.sh
```

- `tools/check.sh` parses every Luau file with the upstream Luau binary
  (downloaded on first run). It catches syntax errors and unused locals. It does
  **not** typecheck against the Roblox API: luau-lsp's `globalTypes.d.luau` uses
  `declare class ... with ... end`, which upstream `luau-analyze` cannot parse,
  so "unknown global" diagnostics are filtered out.
- `tools/validate_bank.py` enforces the question authoring rules. Besides the
  per-question checks it looks for two bank-wide patterns children find fast: the
  correct answer being uniquely the longest option, and answers clustering in one
  slot. Either turns a test of understanding into a test of pattern-spotting.
- `tools/simulate_economy.py` reads its constants straight out of the Luau
  sources, so it cannot drift from the game, and verifies both economic claims —
  the ad catch-up band, and that every farming route earns less than honest
  teaching.

## Opening in Studio

Requires [Rojo](https://rojo.space) and [Wally](https://wally.run).

```sh
wally install
rojo serve
```

Then connect from the Rojo plugin in Studio.

## Before this can take money

Ad and purchase ids in `src/shared/Config/Monetization.luau` are all `0`, which
the services treat as "not configured" and refuse to sell. Fill them in from the
Creator Hub after creating each pass and product.

Three things gate revenue and none of them are code:

1. **Ads need 2,000 unique monthly visitors**, a 13+ ID-verified account with 2FA,
   and an approved Maturity & Compliance questionnaire. Declare the moderation
   pipeline honestly there, and confirm with Roblox Support that it clears the
   free-form bar before scaling.
2. **DevEx is the only legal way out.** Roblox's terms void any sale of
   in-experience content for money outside the platform, and attempting it
   disqualifies the account from DevEx permanently. No external processor touches
   this game, ever.
3. **Tax information must be filed before 31 October 2026.** DevEx payments
   become royalties on 1 November; without a valid form up to 24% is withheld
   from the whole payout, and with one it is 0–30% on the US-player share
   depending on the treaty that covers your residence.

## Moving this into its own repository

It lives in a subdirectory because the GitHub integration for this session could
not create repositories (`403 Resource not accessible by integration`). To split
it out with its history intact:

```sh
git subtree split --prefix=roblox-school -b roblox-school-only
# create the empty repo on GitHub, then
git push git@github.com:<owner>/roblox-school.git roblox-school-only:main
```

## State

Done: project skeleton, shared types and config, profile storage with session
locking, idempotent receipts, the rewarded-video flow, rate limiting, a seeded
question bank and the three checks above.

Next, in order: subject mechanics (quizzes, obstacle courses, assembly), grade
progression through to graduation, player teachers and the payout formula in
`Economy.luau`, the authoring and moderation pipeline, campuses and elections,
then translation.
