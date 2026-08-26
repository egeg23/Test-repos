#!/usr/bin/env python3
"""Checks the election calendar and the limits on what a director can do.

The phase of the cycle is derived from the clock on every server independently,
so an off-by-one at a boundary does not fail loudly -- it means two servers
disagree about whether voting is open, and the bug surfaces as votes that
sometimes count. Worth walking every day of the cycle.

The second half asserts the anti-griefing invariant: every power the office has
multiplies upward. A director who can subtract is a director who will.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "src/shared/Config/Campus.luau"
TEXT = CONFIG.read_text(encoding="utf-8")


def scalar(name: str) -> float:
    """Reads a constant, including ones written as a product like `12 * 3600`.

    An earlier version stopped at the first number and read that constant as 12
    instead of 43200, then cheerfully reported that everything passed while
    measuring something the game does not do. So anything this cannot fully
    parse is now fatal rather than partially understood.
    """
    match = re.search(rf"^Campus\.{name}\s*=\s*([^\n-]+)", TEXT, re.MULTILINE)
    if not match:
        raise SystemExit(f"check_campus: could not read Campus.{name}")

    expression = match.group(1).strip()
    if not re.fullmatch(r"[0-9.]+(\s*\*\s*[0-9.]+)*", expression):
        raise SystemExit(
            f"check_campus: Campus.{name} is {expression!r}, which this parser "
            f"cannot evaluate -- teach it the new form before trusting the result."
        )

    value = 1.0
    for factor in expression.split("*"):
        value *= float(factor.strip())
    return value


EPOCH = int(scalar("Epoch"))
SECONDS_PER_DAY = int(scalar("SecondsPerDay"))
CYCLE_DAYS = int(scalar("CycleDays"))
CAMPAIGN_START = int(scalar("CampaignStartDay"))
VOTING_START = int(scalar("VotingStartDay"))
WEIGHT_CAP = scalar("VoteWeightCap")
SECONDS_PER_WEIGHT = scalar("SecondsPerExtraVoteWeight")
MIN_PLAY = scalar("MinPlaySecondsToVote")
MIN_AGE = scalar("MinAccountAgeDaysToVote")


def cycle_index(now: int) -> int:
    return (now - EPOCH) // (CYCLE_DAYS * SECONDS_PER_DAY)


def day_in_cycle(now: int) -> int:
    return ((now - EPOCH) % (CYCLE_DAYS * SECONDS_PER_DAY)) // SECONDS_PER_DAY


def phase(now: int) -> str:
    day = day_in_cycle(now)
    if day >= VOTING_START:
        return "voting"
    if day >= CAMPAIGN_START:
        return "campaign"
    return "term"


def weight(play_seconds: float) -> float:
    return min(max(1 + play_seconds / SECONDS_PER_WEIGHT, 1), WEIGHT_CAP)


def main() -> int:
    failures: list[str] = []

    print("=" * 70)
    print("Election calendar")
    print("=" * 70)
    print(f"  cycle {CYCLE_DAYS} days: term 0..{CAMPAIGN_START - 1}, "
          f"campaign {CAMPAIGN_START}..{VOTING_START - 1}, "
          f"voting {VOTING_START}..{CYCLE_DAYS - 1}")

    if not 0 < CAMPAIGN_START < VOTING_START < CYCLE_DAYS:
        failures.append("phase boundaries are out of order")

    # Walk every day of two whole cycles at both edges of the day, which is where
    # an off-by-one lives.
    seen: dict[str, int] = {"term": 0, "campaign": 0, "voting": 0}
    for cycle in range(2):
        for day in range(CYCLE_DAYS):
            for offset in (0, SECONDS_PER_DAY - 1):
                now = EPOCH + (cycle * CYCLE_DAYS + day) * SECONDS_PER_DAY + offset
                if cycle_index(now) != cycle:
                    failures.append(f"cycle index wrong at cycle {cycle} day {day}")
                if day_in_cycle(now) != day:
                    failures.append(f"day-in-cycle wrong at cycle {cycle} day {day}")
                if cycle == 0:
                    seen[phase(now)] += 1

    expected = {
        "term": CAMPAIGN_START * 2,
        "campaign": (VOTING_START - CAMPAIGN_START) * 2,
        "voting": (CYCLE_DAYS - VOTING_START) * 2,
    }
    for name, count in seen.items():
        status = "ok " if count == expected[name] else "NO "
        print(f"  {status} {name:<9} covers {count // 2} days (expected {expected[name] // 2})")
        if count != expected[name]:
            failures.append(f"{name} covers the wrong number of days")

    # The boundary between the last day of one cycle and the first of the next.
    last = EPOCH + (CYCLE_DAYS * SECONDS_PER_DAY) - 1
    first = last + 1
    if cycle_index(last) != 0 or cycle_index(first) != 1:
        failures.append("the cycle does not roll over cleanly at its boundary")
    else:
        print("  ok  the cycle rolls over cleanly on the second it should")
    if phase(last) != "voting" or phase(first) != "term":
        failures.append("voting does not hand straight over to a new term")
    else:
        print("  ok  voting hands straight over to a new term")

    print()
    print("=" * 70)
    print("Vote weight")
    print("=" * 70)
    for hours in (0, 1, 6, 12, 24, 48, 200):
        print(f"  {hours:>4}h played -> weight {weight(hours * 3600):.2f}")
    if weight(0) != 1:
        failures.append("a brand new voter does not start at weight 1")
    if weight(10**9) > WEIGHT_CAP:
        failures.append("vote weight is not capped")
    else:
        print(f"  ok  capped at {WEIGHT_CAP:.0f}, so alts cannot be stacked without limit")
    if MIN_PLAY <= 0 or MIN_AGE <= 0:
        failures.append("voting has no eligibility floor at all")
    else:
        print(f"  ok  must be {MIN_AGE:.0f} days old and have played "
              f"{MIN_PLAY / 60:.0f} minutes to vote")

    print()
    print("=" * 70)
    print("Director powers only ever add")
    print("=" * 70)
    powers = {
        "SubjectOfMonthMultiplier": scalar("SubjectOfMonthMultiplier"),
        "EventMultiplier": scalar("EventMultiplier"),
        "DirectorShare": scalar("DirectorShare"),
    }
    for name, value in powers.items():
        floor = 1.0 if "Multiplier" in name else 0.0
        ok = value >= floor
        print(f"  {'ok ' if ok else 'NO '} {name:<28} {value}  (must be >= {floor})")
        if not ok:
            failures.append(f"{name} can reduce what a player gets")

    # A director's cut has to be small enough that it is not worth farming.
    if powers["DirectorShare"] > 0.1:
        failures.append("the director's share is large enough to be worth gaming")
    else:
        print("  ok  the director's cut is too small to be worth farming")

    print()
    if failures:
        for failure in sorted(set(failures)):
            print(f"  - {failure}")
        print(f"\nFAILED: {len(set(failures))} problem(s).")
        return 1
    print("All campus checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
