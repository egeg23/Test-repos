#!/usr/bin/env python3
"""Checks the achievement branches against the rest of the game.

The Luau spec covers the arithmetic. What it cannot cover is agreement with
modules it is unable to require -- the server services import through Roblox
instance paths, so a stat that no service ever increments, or a threshold that
disagrees with the code feeding it, is invisible to the tests.

Three of those, all of which are silent at run time:

  * A branch keyed to a stat nothing writes. The branch renders, the bar never
    moves, and the player concludes the game is broken.
  * A service bumping a stat no branch counts. Harmless, but it means someone
    intended a branch that is not there.
  * The mastery threshold. AchievementService cannot require RewardService
    (that would be a cycle), so it holds its own copy. A copy nobody checks is
    a copy that drifts.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = (ROOT / "src/shared/Config/Achievements.luau").read_text(encoding="utf-8")
SERVICE = (ROOT / "src/server/Services/AchievementService.luau").read_text(encoding="utf-8")
REWARD = (ROOT / "src/server/Services/RewardService.luau").read_text(encoding="utf-8")
SERVER = list((ROOT / "src/server").rglob("*.luau"))

problems: list[str] = []

# --- every branch's stat is written by something -------------------------------

declared = dict(re.findall(r'id = "(\w+)",\s*\n\s*stat = "(\w+)"', CONFIG))
if not declared:
    raise SystemExit("check_achievements: could not read the branch list")

written: set[str] = set()
for path in SERVER:
    text = path.read_text(encoding="utf-8")
    written |= set(re.findall(r'AchievementService\.(?:bump|record)\(\s*\w+,\s*"(\w+)"', text))
    # Teacher counters are delivered through the payout queue, because the
    # teacher is usually offline when a student moves them.
    written |= set(re.findall(r'creditStat\(\s*[\w.]+,\s*"(\w+)"', text))
    # And two are seeded from existing profile fields on load.
    written |= set(re.findall(r'record\(player, "(\w+)"', text))

for branch, stat in sorted(declared.items()):
    if stat not in written:
        problems.append(f"branch '{branch}' counts '{stat}', which no service ever writes")

for stat in sorted(written - set(declared.values())):
    problems.append(f"a service writes stat '{stat}', which no branch counts")

# --- the duplicated mastery threshold ------------------------------------------

service_value = re.search(r"local MASTERY_LESSONS = (\d+)", SERVICE)
reward_value = re.search(r"RewardService\.LessonsToMasterSubject = (\d+)", REWARD)
if not service_value or not reward_value:
    problems.append("could not read the mastery threshold from both sides")
elif service_value.group(1) != reward_value.group(1):
    problems.append(
        f"mastery threshold disagrees: AchievementService says {service_value.group(1)}, "
        f"RewardService says {reward_value.group(1)}"
    )

# --- every branch is reachable from the string table ---------------------------

strings = (ROOT / "src/shared/Strings.luau").read_text(encoding="utf-8")
for branch in sorted(declared):
    key = f'["achv.{branch}"]'
    if key not in strings:
        problems.append(f"branch '{branch}' has no string entry {key}")

# Every perk effect needs a label, or the panel prints a raw key.
for effect in sorted(set(re.findall(r'effect = "(\w+)"', CONFIG))):
    if f'["perk.{effect}"]' not in strings:
        problems.append(f"perk effect '{effect}' has no string entry [\"perk.{effect}\"]")

print(f"  {len(declared)} branches, {len(written)} stats written by services")
print(f"  mastery threshold {reward_value.group(1) if reward_value else '?'} on both sides")

if problems:
    for problem in problems:
        print(f"  FAIL: {problem}")
    sys.exit(1)
print("All achievement checks passed.")
