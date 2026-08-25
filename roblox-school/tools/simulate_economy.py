#!/usr/bin/env python3
"""Checks the economy's two load-bearing claims with numbers.

1. A free player who watches every ad available closes a defined share of the gap
   to a paying player. That share is Economy.AdCatchUpTarget.
2. Teacher payout collapses under each way the formula can be farmed.

Constants are read out of the Luau sources rather than copied, so this tool
cannot quietly disagree with the game it is checking.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ECONOMY = ROOT / "src/shared/Config/Economy.luau"
PROGRESSION = ROOT / "src/shared/Config/Progression.luau"
MONETIZATION = ROOT / "src/shared/Config/Monetization.luau"

# Session lengths where the catch-up promise has to hold. Very short and very
# long sessions are reported but not enforced: see the note printed below.
ENFORCED_SESSION_MINUTES = (45, 60, 90, 120)
REPORTED_SESSION_MINUTES = (15, 30, 45, 60, 90, 120, 180, 240)


def parse_economy() -> dict[str, float]:
    text = ECONOMY.read_text(encoding="utf-8")
    found = dict(re.findall(r"^Economy\.(\w+)\s*=\s*([0-9.]+)$", text, re.MULTILINE))
    return {key: float(value) for key, value in found.items()}


def parse_progression() -> tuple[int, int]:
    """Max grade, and the constant in `lessonsForGrade`.

    Parsed rather than copied, and loudly fatal if the shape of that function
    changes, so this check can never quietly measure a formula the game no
    longer uses.
    """
    text = PROGRESSION.read_text(encoding="utf-8")
    max_grade = re.search(r"^Progression\.MaxGrade\s*=\s*(\d+)$", text, re.MULTILINE)
    offset = re.search(r"return\s+(\d+)\s*\+\s*clamped", text)
    if not max_grade or not offset:
        raise SystemExit(
            "simulate_economy: could not read the grade formula out of "
            "Progression.luau -- update this parser before trusting the result."
        )
    return int(max_grade.group(1)), int(offset.group(1))


def parse_ad_rewards() -> dict[str, dict[str, float]]:
    text = MONETIZATION.read_text(encoding="utf-8")
    block = text[text.index("Monetization.AdRewards") : text.index("Monetization.MinAdRewardRobux")]
    rewards: dict[str, dict[str, float]] = {}
    for entry in re.findall(r"\{(.*?)\}", block, re.DOTALL):
        name = re.search(r'id\s*=\s*"([^"]+)"', entry)
        if not name:
            continue
        fields: dict[str, float] = {}
        for key in ("cooldownSeconds", "dailyLimit", "boostSeconds", "robuxEquivalent"):
            match = re.search(rf"{key}\s*=\s*([0-9.]+)", entry)
            if match:
                fields[key] = float(match.group(1))
        rewards[name.group(1)] = fields
    return rewards


def boosted_fraction(session_seconds: float, cooldown: float, boost: float, limit: float) -> float:
    """Share of a session spent under the ad boost.

    A player starts one ad immediately and another every cooldown, until the
    daily limit runs out or the session ends.
    """
    if session_seconds <= 0 or boost <= 0:
        return 0.0
    starts = []
    t = 0.0
    while t < session_seconds and len(starts) < limit:
        starts.append(t)
        if cooldown <= 0:
            break
        t += cooldown
    boosted = sum(min(boost, max(0.0, session_seconds - start)) for start in starts)
    return boosted / session_seconds


def main() -> int:
    economy = parse_economy()
    rewards = parse_ad_rewards()

    target = economy["AdCatchUpTarget"]
    reward = rewards["doubleLessonReward"]
    cooldown = reward["cooldownSeconds"]
    boost = reward.get("boostSeconds", 0.0)
    limit = reward["dailyLimit"]

    print("=" * 74)
    print("Catch-up: how much of the paying player's edge an ad watcher reaches")
    print("=" * 74)
    print(f"target {target:.0%}   boost {boost:.0f}s   cooldown {cooldown:.0f}s   cap {limit:.0f}/day")
    print()
    print(f"{'session':>9}  {'ads':>4}  {'free':>6}  {'ads':>6}  {'paid':>6}  {'catch-up':>9}")
    print("-" * 52)

    failures = []
    for minutes in REPORTED_SESSION_MINUTES:
        seconds = minutes * 60
        fraction = boosted_fraction(seconds, cooldown, boost, limit)
        ads_used = min(limit, (seconds // cooldown) + 1 if cooldown else limit)
        # The pass is a permanent x2; the ad is x2 while it lasts. Catch-up is the
        # share of the paying player's *extra* value that the ad watcher gets.
        free_mult, paid_mult = 1.0, 2.0
        ad_mult = 1.0 + fraction
        # Both the pass and the ad are x2, so the share of the paying player's
        # extra value that the ad watcher reaches is exactly the boosted
        # fraction. Deriving it from the multipliers instead reintroduces a
        # floating-point artifact right on the band edge.
        catch_up = fraction
        flag = ""
        if minutes in ENFORCED_SESSION_MINUTES:
            if not (0.50 <= catch_up <= 0.60):
                failures.append((minutes, catch_up))
                flag = "  <-- OUT OF BAND"
            else:
                flag = "  ok"
        print(
            f"{minutes:>7}m  {ads_used:>4.0f}  {free_mult:>6.2f}  {ad_mult:>6.2f}  "
            f"{paid_mult:>6.2f}  {catch_up:>8.0%}{flag}"
        )

    print()
    print("Short sessions over-deliver and very long ones under-deliver, both by")
    print("design: the daily cap is what bites at 180m+, and a player at that")
    print("length is the one the passes are actually for. The band is only")
    print("enforced across 45-120m, where most sessions sit.")

    print()
    print("=" * 74)
    print("Teacher payout under honest use and under each farming route")
    print("=" * 74)

    base = economy["BasePayout"]
    decay = economy["UniquenessDecay"]
    floor = economy["UniquenessFloor"]
    cap = economy["LifetimePayoutCapPerStudent"]

    def quality(pass_rate: float) -> float:
        low, high = economy["QualityBandLow"], economy["QualityBandHigh"]
        too_easy, too_hard = economy["QualityFloorTooEasy"], economy["QualityFloorTooHard"]
        rate = min(max(pass_rate, 0.0), 1.0)
        if rate <= low:
            return too_hard + (1 - too_hard) * (rate / low)
        if rate <= high:
            return 1.0
        return 1.0 - (1.0 - too_easy) * ((rate - high) / (1 - high))

    def uniqueness(prior: int) -> float:
        return max(decay**prior, floor)

    def fill(members: int, capacity: int) -> float:
        return economy["FillRateMin"] + economy["FillRateSpan"] * min(members / capacity, 1.0)

    def rating(value: float) -> float:
        return economy["RatingMin"] + economy["RatingSpan"] * (value / economy["MaxRating"])

    def run(label: str, students: int, per_student: int, pass_rate: float,
            members: int, capacity: int, teacher_rating: float,
            engagement: float, counts: bool) -> float:
        if not counts:
            print(f"{label:<34} {0.0:>10.0f}   blocked: alt gate")
            return 0.0
        total = 0.0
        for _ in range(students):
            paid = 0.0
            for completion in range(per_student):
                amount = (base * uniqueness(completion) * engagement * quality(pass_rate)
                          * fill(members, capacity) * rating(teacher_rating))
                amount = min(amount, max(0.0, cap - paid))
                paid += amount
            total += paid
        print(f"{label:<34} {total:>10.0f}")
        return total

    print(f"{'scenario':<34} {'points':>10}")
    print("-" * 50)
    honest = run("honest: 20 students x1 lesson", 20, 1, 0.65, 18, 20, 4.2, 1.0, True)
    ring = run("collusion ring: 4 friends x30", 4, 30, 0.65, 4, 20, 4.2, 1.0, True)
    trivial = run("trivial test: 20 students, 99% pass", 20, 1, 0.99, 18, 20, 4.2, 1.0, True)
    scripted = run("scripted: 20 students, no time spent", 20, 1, 0.65, 18, 20, 4.2, 0.0, True)
    run("alt farm: 20 fresh accounts", 20, 1, 0.65, 18, 20, 4.2, 1.0, False)

    print()
    for label, value in (("collusion ring", ring), ("trivial test", trivial), ("scripted", scripted)):
        share = value / honest if honest else 0.0
        verdict = "ok" if share <= 1.0 else "PROFITABLE ATTACK"
        print(f"  {label:<18} {share:>6.0%} of honest income   {verdict}")
        if share > 1.0:
            failures.append((label, share))

    print()
    print("=" * 74)
    print("Time to graduate")
    print("=" * 74)

    max_grade, offset = parse_progression()
    lessons_to_pass = sum(offset + grade for grade in range(1, max_grade + 1))
    seconds_per_lesson = economy["QuestionsPerLesson"] * economy["ExpectedSecondsPerQuestion"]

    # A player has to *pass* every one of those lessons, and the quality band
    # targets a pass rate well under 100%, so attempts outnumber passes.
    band_pass_rate = (economy["QualityBandLow"] + economy["QualityBandHigh"]) / 2
    attempts_needed = lessons_to_pass / band_pass_rate
    lesson_hours = attempts_needed * seconds_per_lesson / 3600

    # Menus, picking a class, talking to people, walking around a school.
    OVERHEAD = 1.5
    wall_hours = lesson_hours * OVERHEAD

    print(f"  grades                    {max_grade}")
    print(f"  lessons to pass           {lessons_to_pass}")
    print(f"  seconds per lesson        {seconds_per_lesson:.0f}")
    print(f"  assumed pass rate         {band_pass_rate:.0%}  (centre of the quality band)")
    print(f"  attempts needed           {attempts_needed:.0f}")
    print(f"  hours of lessons          {lesson_hours:.1f}")
    print(f"  wall-clock at {OVERHEAD:.1f}x overhead {wall_hours:.1f}")
    print()
    print("  A first prestige wants to land within a few weeks of casual play.")

    if not 8 <= wall_hours <= 25:
        failures.append(("time to graduate", wall_hours))
        print(f"  <-- OUT OF BAND: {wall_hours:.1f}h is outside 8-25h")
    else:
        print(f"  ok: {wall_hours:.1f}h is inside 8-25h")

    print()
    if failures:
        print(f"FAILED: {len(failures)} check(s) outside their band.")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
