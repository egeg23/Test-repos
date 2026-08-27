#!/usr/bin/env python3
"""Checks that every room can be built, and that no room can melt a phone.

Three drifts this catches, all of which are silent at run time:

  * A subject added to Subjects.luau with no theme in Decor.luau. The builder
    falls back to Decor.Default, so the room appears -- looking exactly like
    every other unthemed room, which is a bug that looks like a decision.
  * An emitter tuned past the particle budget. Rate times lifetime is how many
    particles a room carries forever; thirty rooms of that is the frame rate.
    The Luau asserts this too, but the assert only fires once someone runs the
    game, and the tuning pass that breaks it happens in an editor.
  * A grade that belongs to no tier, or to two. Tiers dress the obstacle courses
    by year, so a gap means a course with no colour and an overlap means the
    first match silently wins.

Everything is parsed out of the Luau rather than duplicated here.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DECOR = (ROOT / "src/shared/Config/Decor.luau").read_text(encoding="utf-8")
SUBJECTS = (ROOT / "src/shared/Config/Subjects.luau").read_text(encoding="utf-8")
AUTHORING = (ROOT / "src/shared/Config/Authoring.luau").read_text(encoding="utf-8")

problems: list[str] = []


def section(name: str) -> str:
    """The body of a `Decor.<name> = { ... }` table, by brace matching.

    Regex cannot balance braces, and these tables are full of nested ones, so
    counting is the honest way to find where the table ends.
    """
    start = DECOR.find(f"Decor.{name} = {{")
    if start < 0:
        raise SystemExit(f"check_decor: could not find Decor.{name}")
    i = DECOR.index("{", start)
    depth = 0
    for j in range(i, len(DECOR)):
        if DECOR[j] == "{":
            depth += 1
        elif DECOR[j] == "}":
            depth -= 1
            if depth == 0:
                return DECOR[i + 1 : j]
    raise SystemExit(f"check_decor: Decor.{name} is not brace-balanced")


# --- every subject has a theme -------------------------------------------------

subject_ids = re.findall(r"\{\s*id\s*=\s*\"([a-z]+)\"", SUBJECTS)
if not subject_ids:
    raise SystemExit("check_decor: could not read the subject list")

themed = set(re.findall(r"^\t([a-z]+) = theme\(", section("Subjects"), re.MULTILINE))
for subject in subject_ids:
    if subject not in themed:
        problems.append(f"subject '{subject}' has no theme in Decor.Subjects")

# The reverse too: a theme for a subject that no longer exists is dead config
# that reads as coverage.
for name in sorted(themed - set(subject_ids)):
    problems.append(f"Decor.Subjects has a theme for '{name}', which is not a subject")

# --- the rooms the builder asks for by name ------------------------------------

halls = set(re.findall(r"^\t([a-z]+) = theme\(", section("Halls"), re.MULTILINE))
world = (ROOT / "src/server/Services/WorldService.luau").read_text(encoding="utf-8")
rooms = (ROOT / "src/server/World/Rooms.luau").read_text(encoding="utf-8")
for asked in sorted(set(re.findall(r"Decor\.forHall\(\"([a-z]+)\"\)", rooms + world))):
    if asked not in halls:
        problems.append(f"a room asks for hall theme '{asked}', which Decor.Halls does not have")

# --- particle budget -----------------------------------------------------------

cap_match = re.search(r"Decor\.MaxLiveParticles = ([0-9]+)", DECOR)
if not cap_match:
    raise SystemExit("check_decor: could not read Decor.MaxLiveParticles")
cap = int(cap_match.group(1))

emissions = re.findall(
    r"(\w+) = \{ rate = ([0-9.]+), lifetime = ([0-9.]+),", section("Emissions")
)
if not emissions:
    raise SystemExit("check_decor: could not read Decor.Emissions")
for name, rate, lifetime in emissions:
    live = float(rate) * float(lifetime)
    if live > cap:
        problems.append(f"effect '{name}' holds {live:g} particles, over the cap of {cap}")

# Every effect a theme names must exist as an emission, or the room silently
# gets no effect at all.
declared = {name for name, _, _ in emissions} | {"none"}
for effect in sorted(set(re.findall(r"effect = \"([a-z]+)\"", DECOR))):
    if effect not in declared:
        problems.append(f"a theme uses effect '{effect}', which Decor.Emissions does not define")

# --- tiers cover every grade exactly once --------------------------------------

tiers = [
    (name, int(lo), int(hi))
    for name, lo, hi in re.findall(
        r"id = \"(\w+)\", minGrade = ([0-9]+), maxGrade = ([0-9]+)", DECOR
    )
]
if not tiers:
    raise SystemExit("check_decor: could not read Decor.Tiers")

# The grade range is Authoring's, not a copy: it is the same 1..11 the whole
# game is built on, and a tier table that covered a different range would be
# wrong in a way this check exists to notice.
min_grade = int(re.search(r"Authoring\.MinGrade = ([0-9]+)", AUTHORING).group(1))
max_grade = int(re.search(r"Authoring\.MaxGrade = ([0-9]+)", AUTHORING).group(1))

for grade in range(min_grade, max_grade + 1):
    covering = [name for name, lo, hi in tiers if lo <= grade <= hi]
    if len(covering) == 0:
        problems.append(f"grade {grade} belongs to no tier")
    elif len(covering) > 1:
        problems.append(f"grade {grade} belongs to {len(covering)} tiers: {', '.join(covering)}")

print(f"  {len(subject_ids)} subjects, all themed")
print(f"  {len(halls)} hall themes, {len(emissions)} effects, cap {cap} particles")
print(f"  {len(tiers)} tiers covering grades {min_grade}..{max_grade}")
for name, lo, hi in tiers:
    print(f"    {name:<8} grades {lo}-{hi}")

if problems:
    for problem in problems:
        print(f"  FAIL: {problem}")
    sys.exit(1)
print("All decor checks passed.")
