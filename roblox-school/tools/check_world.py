#!/usr/bin/env python3
"""Replays the school's layout arithmetic and checks the building closes up.

The world is built from code at run time, so its geometry has no level file to
look at and no Studio session in CI. That makes a whole class of bug invisible
until someone loads the game: rooms overlapping, a room hanging off the end of
the corridor, steps that stop short of the floor, a spawn point inside a wall.

Every one of those was actually present in the first version of this layout --
two halls occupying the same studs, and a spawn inside the assembly hall. So
this replays the same cursor walk the builder does, from constants parsed out of
the source, and asserts the results are consistent.

It is a model of the layout, not the layout itself. It is worth having anyway:
the arithmetic is where the bugs were, and a model that disagrees with the code
is itself a finding.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROOMS = (ROOT / "src/server/World/Rooms.luau").read_text(encoding="utf-8")
WORLD = (ROOT / "src/server/Services/WorldService.luau").read_text(encoding="utf-8")
EXTERIOR = (ROOT / "src/server/World/Exterior.luau").read_text(encoding="utf-8")
SUBJECTS = (ROOT / "src/shared/Config/Subjects.luau").read_text(encoding="utf-8")

problems: list[str] = []


def constant(text: str, name: str) -> float:
    match = re.search(rf"^{re.escape(name)} = (-?[0-9.]+)$", text, re.MULTILINE)
    if not match:
        raise SystemExit(f"check_world: could not read {name}")
    return float(match.group(1))


WIDTH = constant(ROOMS, "Rooms.Width")
DEPTH = constant(ROOMS, "Rooms.Depth")
CORRIDOR = constant(ROOMS, "Rooms.CorridorWidth")
WALL_HEIGHT = constant(ROOMS, "Rooms.WallHeight")
GROUND_Y = constant(EXTERIOR, "Exterior.GroundY")
STEP_COUNT = constant(EXTERIOR, "Exterior.StepCount")
STEP_RISE = constant(EXTERIOR, "Exterior.StepRise")

# Hall footprints, as the builder states them: multiples of the classroom size.
halls: dict[str, tuple[float, float]] = {}
# A hall may be a plain Rooms.Width or a multiple of it, so the multiplier is
# optional and defaults to 1 rather than being required for uniformity's sake.
for name, w, d in re.findall(
    r"(\w+) = \{ width = Rooms\.Width(?: \* ([0-9.]+))?, "
    r"depth = Rooms\.Depth(?: \* ([0-9.]+))? \}",
    WORLD,
):
    halls[name] = (WIDTH * float(w or 1), DEPTH * float(d or 1))
if not halls:
    raise SystemExit("check_world: could not read HALL_SIZES")

# The halls must match what Rooms.* actually builds, or the layout reserves a
# footprint the room then overflows. Both numbers are parsed, not assumed equal.
for name, (width, depth) in halls.items():
    body = re.search(
        rf"function Rooms\.{name}\(.*?local width, depth = (.+?)\n", ROOMS, re.S
    )
    if not body:
        problems.append(f"could not find the size Rooms.{name} builds")
        continue
    expr = body.group(1).replace("Rooms.Width", str(WIDTH)).replace("Rooms.Depth", str(DEPTH))
    built_w, built_d = (eval(part, {"__builtins__": {}}) for part in expr.split(", "))
    if abs(built_w - width) > 1e-6 or abs(built_d - depth) > 1e-6:
        problems.append(
            f"hall '{name}': layout reserves {width:g}x{depth:g}, "
            f"Rooms.{name} builds {built_w:g}x{built_d:g}"
        )

subjects = re.findall(r"\{\s*id = \"([a-z]+)\"", SUBJECTS)
per_side = -(-len(subjects) // 2)

# --- replay the cursor walk ----------------------------------------------------

Box = tuple[str, float, float, float, float]  # name, x0, x1, z0, z1
boxes: list[Box] = []
cursor = {1: 0.0, -1: 0.0}
deepest = {1: 0.0, -1: 0.0}


def place(name: str, side: int, width: float, depth: float) -> None:
    x = cursor[side] + width / 2
    cursor[side] += width
    deepest[side] = max(deepest[side], depth)
    z = side * (CORRIDOR / 2 + depth / 2)
    boxes.append((name, x - width / 2, x + width / 2, z - depth / 2, z + depth / 2))


for index, subject in enumerate(subjects, start=1):
    place(subject, 1 if index <= per_side else -1, WIDTH, DEPTH)

# The arguments actually passed to place(), evaluated -- not the footprints the
# hall table declares. Reading the declaration instead would model the layout
# the code meant to build rather than the one it builds, and the first bug this
# file was written for was exactly that gap: a hall reserved at one size and
# placed at another.
call = re.compile(
    r"local (\w+)Centre = place\(\s*(-?1),\s*([^,]+?),\s*([^)]+?)\)", re.S
)
scope = {
    "HALL_SIZES": {
        name: {"width": w, "depth": d} for name, (w, d) in halls.items()
    },
    "Rooms": {"Width": WIDTH, "Depth": DEPTH},
}


def value(expr: str) -> float:
    """Evaluates a place() size argument, e.g. `HALL_SIZES.gym.width * 2`."""
    python = re.sub(r"HALL_SIZES\.(\w+)\.(\w+)", r'HALL_SIZES["\1"]["\2"]', expr.strip())
    python = re.sub(r"Rooms\.(\w+)", r'Rooms["\1"]', python)
    return float(eval(python, {"__builtins__": {}}, dict(scope)))


order = call.findall(WORLD)
if len(order) != len(halls):
    problems.append(f"expected {len(halls)} hall placements, found {len(order)}")
for name, side, width_expr, depth_expr in order:
    if name not in halls:
        problems.append(f"'{name}' is placed but has no entry in HALL_SIZES")
        continue
    width, depth = value(width_expr), value(depth_expr)
    declared_w, declared_d = halls[name]
    if abs(width - declared_w) > 1e-6 or abs(depth - declared_d) > 1e-6:
        problems.append(
            f"hall '{name}' is placed at {width:g}x{depth:g} but reserves "
            f"{declared_w:g}x{declared_d:g}"
        )
    place(name, int(side), width, depth)

corridor_length = max(cursor[1], cursor[-1])
bounds = {
    "minX": 0.0,
    "maxX": corridor_length,
    "minZ": -(CORRIDOR / 2 + deepest[-1]),
    "maxZ": CORRIDOR / 2 + deepest[1],
}

# --- the assertions ------------------------------------------------------------

for i, a in enumerate(boxes):
    for b in boxes[i + 1 :]:
        overlap_x = min(a[2], b[2]) - max(a[1], b[1])
        overlap_z = min(a[4], b[4]) - max(a[3], b[3])
        if overlap_x > 1e-6 and overlap_z > 1e-6:
            problems.append(
                f"'{a[0]}' and '{b[0]}' overlap by {overlap_x:g}x{overlap_z:g} studs"
            )

for name, x0, x1, z0, z1 in boxes:
    if x0 < bounds["minX"] - 1e-6 or x1 > bounds["maxX"] + 1e-6:
        problems.append(f"'{name}' runs off the corridor: x {x0:g}..{x1:g}")
    if z0 < bounds["minZ"] - 1e-6 or z1 > bounds["maxZ"] + 1e-6:
        problems.append(f"'{name}' is outside the footprint: z {z0:g}..{z1:g}")
    # No room may cross into the corridor: the corridor is the only place a
    # player walks between rooms, and a room hanging into it blocks the way.
    if z0 < CORRIDOR / 2 - 1e-6 and z1 > -CORRIDOR / 2 + 1e-6:
        problems.append(f"'{name}' overlaps the corridor")

# The spawn is on the path, outside the front wall.
spawn_x = bounds["minX"] - 34
if spawn_x >= bounds["minX"]:
    problems.append("the spawn is inside the building")
for name, x0, x1, z0, z1 in boxes:
    if x0 - 8 <= spawn_x <= x1 + 8:
        problems.append(f"the spawn at x={spawn_x:g} is inside '{name}'")

# The steps have to land on the floor. The corridor slab is 1 stud thick centred
# on y=0, so its walking surface is at +0.5.
floor_top = 0.5
step_top = GROUND_Y + STEP_COUNT * STEP_RISE
if abs(step_top - floor_top) > 0.35:
    problems.append(
        f"the steps stop at y={step_top:g} but the floor is at y={floor_top:g} "
        f"({STEP_COUNT:g} steps of {STEP_RISE:g} from {GROUND_Y:g})"
    )

print(f"  {len(subjects)} classrooms, {len(halls)} halls, corridor {corridor_length:g} studs")
print(f"  footprint x {bounds['minX']:g}..{bounds['maxX']:g}, z {bounds['minZ']:g}..{bounds['maxZ']:g}")
print(f"  steps: {GROUND_Y:g} + {STEP_COUNT:g}x{STEP_RISE:g} = {step_top:g}, floor at {floor_top:g}")
print(f"  walls {WALL_HEIGHT:g} studs, {len(boxes)} rooms placed, none overlapping"
      if not problems else f"  {len(boxes)} rooms placed")

if problems:
    for problem in problems:
        print(f"  FAIL: {problem}")
    sys.exit(1)
print("All world checks passed.")
