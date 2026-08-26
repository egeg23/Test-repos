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
  (downloaded on first run) and gates on syntax errors and lints.

  It deliberately does **not** gate on type errors, and it is worth knowing why.
  Requires here are Roblox instance paths (`ReplicatedStorage.Shared.Types`),
  which no file-based tool can resolve, so every type imported from another
  module degrades to an error type and the checker then invents a structure from
  how the value happens to be used. The result is long cascades of
  confident-looking nonsense — "does not have key 'grade'" about a field that is
  plainly declared. This was confirmed by handing the checker identical code with
  a local type declaration, which passes clean. Type diagnostics are counted and
  suppressed; real typechecking needs luau-lsp with a Rojo sourcemap, in Studio
  or an editor.
- `tools/check_obstacles.py` measures the obstacle difficulty curve against what
  a Roblox character can physically do — it clears roughly twenty studs at a run
  and is about two wide — and asserts the final year actually reaches the edge of
  that while the first stays gentle.
- `tools/validate_bank.py` enforces the question authoring rules, reading them
  from the shared `Authoring` config so the bank and teacher-written questions
  are held to one standard.
- `tools/validate_assembly.py` checks assembly tasks against the component
  catalogue. Two of its failures are silent rather than loud: a task whose answer
  is not in its own palette is unsolvable but reads fine, and a palette holding
  only the pieces it needs solves itself by elimination.
- `tools/check_campus.py` walks every day of the election cycle at both edges.
  The phase is derived from the clock on each server independently, so an
  off-by-one does not fail loudly — it means two servers disagree about whether
  voting is open. It also asserts that every power the director's office holds
  multiplies upward.
- `tools/check_requires.py` looks for circular requires. Luau resolves a cycle by
  erroring at runtime, and only on the load order that happens to hit it, so one
  can sit in a build for weeks and then break in front of players. Nothing else
  here can see it — the syntax checker reads one file at a time. Besides the
  per-question checks it looks for two bank-wide patterns children find fast: the
  correct answer being uniquely the longest option, and answers clustering in one
  slot. Either turns a test of understanding into a test of pattern-spotting.
- `tools/simulate_economy.py` reads its constants straight out of the Luau
  sources, so it cannot drift from the game. It verifies the ad catch-up band,
  that every farming route earns less than honest teaching, that a fuller class
  pays more per student, that the capacity pass never lowers the buyer's income,
  and that the run to graduation lands in a sane number of hours. If the shape of
  a parsed formula changes it aborts rather than quietly measuring a formula the
  game no longer uses.

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

The economy is live end to end. A graduate takes the teaching branch and is
licensed, creates a class, assembles a lesson from bank questions, and is paid
when students take it — decayed for repeats, scaled by their rating and how full
the class is, capped per student, and blocked entirely for fresh alts. Payment
reaches them whether or not they were online for it.

Students browse a ranked class directory for their language, join one class at a
time, take its lessons, and rate it. Lessons still work with nobody teaching:
the curated bank runs the school at three in the morning.

Also done: profile storage with session locking, idempotent receipts, the
rewarded-video flow, cross-server pass-rate statistics, rate limiting, and text
filtering on everything a player types before it reaches anyone else.

PE runs on obstacle courses, the one subject where a teacher creates without
typing a word. A course is an ordered list of prefab modules and a target grade;
prefab assembly is outside the free-form rules entirely, so a course is live the
moment it is saved. Difficulty belongs to the grade rather than the module, so
one catalogue serves the whole school: the same gap is four studs for a
first-year and eighteen for a final-year. A teacher may set a course one grade
either side of their class and no further — the quality factor would eventually
punish a trivial course through its pass rate, but that takes twenty attempts,
and those are twenty students who wasted their time.

Science and art run on assembly tasks — labelled slots, a palette with spare
pieces, marked on the server. The teacher picks which tasks to set; the catalogue
decides what is correct, because a teacher who could declare which wiring is
right could teach the wrong one.

Teachers can also write their own questions. That is free text, so it goes
through structural rules, then TextService on every field, then a hold, then
publication — each step failing closed, and nothing resolvable until it reaches
the end. Universal subjects are machine-translated into the other launch locales
and filtered again before storage.

Each language has its own campus with a monthly election. Phases come from the
clock rather than a scheduler, and every power the office holds multiplies
upward.

A teacher can also run a class live: they push each question when the room is
ready and decide when the answer is revealed, and both sides earn more for
having turned up. Option order is shuffled per participant rather than per
session — in a room of children answering the same question at the same moment,
one shared "it's B" would otherwise settle it for everyone.

A live session lives on one server. Spanning servers would need MessagingService
and a different design; the matchmaking signals exist partly so that classmates
land together in the first place.

One design consequence worth knowing: grades ten and eleven have no checkpoints,
so a single fall ends the run with nothing scored. That is the intent — the final
year is meant to be genuinely hard — but it is the first thing to revisit if
retention data says the last two grades are where players stop.

Ids in `Monetization.luau` are still `0`, so nothing can actually be sold until
they are filled in from the Creator Hub.
