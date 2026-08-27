#!/usr/bin/env python3
"""Holds the limit constants to the code that enforces them.

Limits.luau is the shared statement of what the shop sells relief from. Two of
its numbers are necessarily duplicated in server code that cannot require across
the boundary cleanly, and a duplicated constant nobody checks is one that drifts:
the day the class lesson cap and Limits.BaseLessonsPerClass disagree, the shop is
selling a slot for a wall that is somewhere else.

Also checks the one claim the Luau spec cannot make on its own -- that the daily
curve, at the point a paying player reaches it, is actually worth the pass.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIMITS = (ROOT / "src/shared/Config/Limits.luau").read_text(encoding="utf-8")
CLASS = (ROOT / "src/server/Services/ClassService.luau").read_text(encoding="utf-8")
PROGRESSION = (ROOT / "src/server/Services/ProgressionService.luau").read_text(encoding="utf-8")

problems: list[str] = []


def number(text: str, pattern: str, what: str) -> float:
    match = re.search(pattern, text)
    if not match:
        raise SystemExit(f"check_limits: could not read {what}")
    return float(match.group(1))


base_lessons = number(LIMITS, r"Limits\.BaseLessonsPerClass = ([0-9.]+)", "BaseLessonsPerClass")
class_cap = number(CLASS, r"local MAX_LESSONS_PER_CLASS = ([0-9.]+)", "MAX_LESSONS_PER_CLASS")
if base_lessons != class_cap:
    problems.append(
        f"lesson cap disagrees: Limits says {base_lessons:g}, ClassService says {class_cap:g}"
    )

full_rate = number(
    LIMITS, r"Limits\.BaseDailyFullRateLessons = ([0-9.]+)", "BaseDailyFullRateLessons"
)
decay = number(LIMITS, r"Limits\.DailyDecayPerLesson = ([0-9.]+)", "DailyDecayPerLesson")
floor = number(LIMITS, r"Limits\.MinDailyRate = ([0-9.]+)", "MinDailyRate")
pass_bonus = number(
    PROGRESSION, r"ProgressionService\.LessonSlotsPassBonus = ([0-9.]+)", "LessonSlotsPassBonus"
)
second_wind = number(LIMITS, r"Limits\.SecondWindLessons = ([0-9.]+)", "SecondWindLessons")

if not 0 < decay < 1:
    problems.append(f"the daily decay of {decay:g} is not a decay")
if floor <= 0:
    problems.append("the daily rate floor is zero, which makes the curve a wall")
if floor >= 1:
    problems.append("the daily rate floor is 1, which means there is no curve")


def rate(lessons: float, extra: float) -> float:
    over = max(0.0, lessons - (full_rate + extra))
    return 1.0 if over <= 0 else max(floor, decay**over)


# The pass has to be worth buying at the point a player meets the curve. Someone
# doing twice the base allowance in a day is the buyer; if the pass barely moves
# their rate, it is being sold on a promise it does not keep.
heavy_day = full_rate * 2
without = rate(heavy_day, 0)
with_pass = rate(heavy_day, pass_bonus)
if with_pass <= without * 1.15:
    problems.append(
        f"the lessonSlots pass is not worth buying: on a {heavy_day:g}-lesson day it moves "
        f"the rate from {without:.2f} to {with_pass:.2f}"
    )

# And it must not be so strong that the curve stops existing for buyers.
if rate(full_rate * 3, pass_bonus) >= 0.95:
    problems.append("the lessonSlots pass removes the curve rather than extending it")

# The second wind has to be worth an ad, and must not be worth more than the pass.
wound_back = rate(max(0.0, heavy_day - second_wind), 0)
if wound_back <= without * 1.05:
    problems.append("the second-wind ad barely changes anything")
if second_wind >= pass_bonus * 2:
    problems.append(
        f"the second wind ({second_wind:g} lessons) is close to the pass ({pass_bonus:g}); "
        "one ad should not be most of a purchase"
    )

print(f"  lesson cap {class_cap:g} on both sides")
print(f"  daily allowance {full_rate:g}, decay {decay:g}/lesson, floor {floor:g}")
print(f"  on a {heavy_day:g}-lesson day: {without:.2f} plain, "
      f"{with_pass:.2f} with the pass, {wound_back:.2f} after one second wind")

if problems:
    for problem in problems:
        print(f"  FAIL: {problem}")
    sys.exit(1)
print("All limit checks passed.")
