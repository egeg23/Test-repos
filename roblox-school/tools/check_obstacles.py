#!/usr/bin/env python3
"""Checks the obstacle difficulty curve against what a Roblox character can do.

The design claim is that a course gets meaningfully harder every year and that
the final year is genuinely difficult. That claim is only worth anything in
studs and seconds, measured against the character: it clears roughly twenty
studs at a full run and is about two studs wide. So a gap near eighteen and a
beam near one and a half are at the edge of possible, and this asserts the last
grade actually gets there while the first stays gentle.

Constants are parsed out of the Luau rather than copied.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "src/shared/Config/Obstacles.luau"

TEXT = CONFIG.read_text(encoding="utf-8")


def scalar(name: str) -> float:
    match = re.search(rf"^(?:local\s+)?{name}\s*=\s*([0-9.]+)$", TEXT, re.MULTILINE)
    if not match:
        raise SystemExit(f"check_obstacles: could not read {name} from Obstacles.luau")
    return float(match.group(1))


def lerp_range(field: str) -> tuple[float, float]:
    """Reads the two ends of a `lerp(a, b, t)` for a named field.

    Tolerates the wrappers actually used in the config -- math.round around the
    module count, and a multiplication in front of the time budget -- so the
    parser follows the source rather than dictating how it must be written.
    """
    match = re.search(
        rf"{field}\s*=\s*(?:math\.round\()?(?:\w+\s*\*\s*)?lerp\("
        rf"([0-9.]+),\s*([0-9.]+),\s*t\)",
        TEXT,
    )
    if not match:
        raise SystemExit(f"check_obstacles: could not read the lerp for {field}")
    return float(match.group(1)), float(match.group(2))


def modules() -> list[tuple[str, int]]:
    found = re.findall(r'\{\s*id\s*=\s*"(\w+)",\s*minGrade\s*=\s*(\d+),', TEXT)
    if not found:
        raise SystemExit("check_obstacles: could not read the module catalogue")
    return [(name, int(grade)) for name, grade in found]


MAX_GRADE = int(scalar("Obstacles.MaxGrade"))
EXPONENT = scalar("DIFFICULTY_EXPONENT")
WINDOW = int(scalar("Obstacles.GradeWindow"))


def difficulty(grade: int) -> float:
    return ((grade - 1) / (MAX_GRADE - 1)) ** EXPONENT


def params(grade: int) -> dict[str, float]:
    t = difficulty(grade)
    out: dict[str, float] = {"difficulty": t}
    for field in ("gapStuds", "beamWidth", "platformSpeed", "vanishSeconds",
                  "spinnerSpeed", "hazardDensity"):
        low, high = lerp_range(field)
        out[field] = low + (high - low) * t

    count_low, count_high = lerp_range("moduleCount")
    out["moduleCount"] = round(count_low + (count_high - count_low) * t)

    time_low, time_high = lerp_range("timeLimitSeconds")
    out["secondsPerModule"] = time_low + (time_high - time_low) * t
    out["timeLimitSeconds"] = out["moduleCount"] * out["secondsPerModule"]

    if grade <= 3:
        out["checkpointEvery"] = 1
    elif grade <= 6:
        out["checkpointEvery"] = 2
    elif grade <= 9:
        out["checkpointEvery"] = 3
    else:
        out["checkpointEvery"] = 0
    return out


def check_builders() -> list[str]:
    """Every declared module must have a builder, and vice versa.

    A module with no builder is not a warning at run time -- buildCourse returns
    nil, the model is destroyed and the student is told the course failed, with
    nothing anywhere saying why. Adding a module is one table entry in a config
    and a function in a service, and the two are in different files.
    """
    service = (ROOT / "src/server/Services/ObstacleService.luau").read_text(encoding="utf-8")
    built = set(re.findall(r"^builders\.(\w+) = function", service, re.MULTILINE))
    declared = set(re.findall(r'\{ id = "(\w+)", minGrade', TEXT))
    found = []
    for name in sorted(declared - built):
        found.append(f"module '{name}' is declared but ObstacleService has no builder for it")
    for name in sorted(built - declared):
        found.append(f"ObstacleService builds '{name}', which is not a declared module")

    # A premium module must not be easier to reach than a free one at the same
    # grade, or the pack would be selling difficulty rather than variety.
    premium = set(re.findall(r'\{ id = "(\w+)"[^}]*premium = true', TEXT))
    for name in sorted(premium):
        entry = re.search(rf'\{{ id = "{name}", minGrade = (\d+)', TEXT)
        if entry and int(entry.group(1)) < 1:
            found.append(f"premium module '{name}' has an impossible minGrade")
    return found


def main() -> int:
    failures: list[str] = []

    print("=" * 78)
    print("Difficulty by grade")
    print("=" * 78)
    print(f"{'grade':>5} {'diff':>6} {'gap':>6} {'beam':>6} {'vanish':>7} "
          f"{'spin':>6} {'mods':>5} {'ckpt':>5} {'limit':>7}")
    print("-" * 60)

    table = {grade: params(grade) for grade in range(1, MAX_GRADE + 1)}
    for grade, p in table.items():
        print(f"{grade:>5} {p['difficulty']:>6.2f} {p['gapStuds']:>6.1f} "
              f"{p['beamWidth']:>6.1f} {p['vanishSeconds']:>7.2f} "
              f"{p['spinnerSpeed']:>6.1f} {p['moduleCount']:>5.0f} "
              f"{p['checkpointEvery']:>5.0f} {p['timeLimitSeconds']:>7.0f}s")

    # Every knob has to move the same way every year, or some grade is a soft spot.
    rising = ("gapStuds", "platformSpeed", "spinnerSpeed", "hazardDensity")
    falling = ("beamWidth", "vanishSeconds")
    for field in rising:
        for grade in range(2, MAX_GRADE + 1):
            if table[grade][field] <= table[grade - 1][field]:
                failures.append(f"{field} does not rise from grade {grade - 1} to {grade}")
    for field in falling:
        for grade in range(2, MAX_GRADE + 1):
            if table[grade][field] >= table[grade - 1][field]:
                failures.append(f"{field} does not fall from grade {grade - 1} to {grade}")

    print()
    print("Final year, against what the character can actually do")
    print("-" * 60)
    last = table[MAX_GRADE]
    hard_checks = [
        ("gap within reach of the ~20 stud jump limit", last["gapStuds"] >= 16,
         f"{last['gapStuds']:.1f} studs"),
        ("beam near the ~2 stud character width", last["beamWidth"] <= 2.0,
         f"{last['beamWidth']:.1f} studs"),
        ("tiles vanish under a second", last["vanishSeconds"] <= 0.7,
         f"{last['vanishSeconds']:.2f}s"),
        ("no checkpoints at all", last["checkpointEvery"] == 0,
         f"{last['checkpointEvery']:.0f}"),
        ("at least 11 modules", last["moduleCount"] >= 11, f"{last['moduleCount']:.0f}"),
        ("under 13s of budget per module", last["secondsPerModule"] <= 13,
         f"{last['secondsPerModule']:.1f}s"),
    ]
    for label, ok, value in hard_checks:
        print(f"  {'ok ' if ok else 'NO '} {label:<48} {value}")
        if not ok:
            failures.append(f"final year: {label} ({value})")

    print()
    print("First year, gentle enough for a seven-year-old")
    print("-" * 60)
    first = table[1]
    easy_checks = [
        ("gap is a step, not a leap", first["gapStuds"] <= 6, f"{first['gapStuds']:.1f} studs"),
        ("beam is a path, not a wire", first["beamWidth"] >= 5, f"{first['beamWidth']:.1f} studs"),
        ("a checkpoint every module", first["checkpointEvery"] == 1, "1"),
    ]
    for label, ok, value in easy_checks:
        print(f"  {'ok ' if ok else 'NO '} {label:<48} {value}")
        if not ok:
            failures.append(f"first year: {label} ({value})")

    # The curve should back-load, not run straight: the last year has to be a
    # long way past the middle, otherwise "harder every year" is just arithmetic.
    ratio = difficulty(MAX_GRADE) / difficulty(6)
    print()
    print(f"  final year is {ratio:.2f}x the difficulty of the middle year")
    if ratio < 2.2:
        failures.append(f"curve is too flat: final/middle is only {ratio:.2f}x")
    else:
        print("  ok: the curve back-loads rather than running straight")

    print()
    print("Every grade can actually be built")
    print("-" * 60)
    catalogue = modules()
    for grade in range(1, MAX_GRADE + 1):
        available = [name for name, min_grade in catalogue if min_grade <= grade]
        count = table[grade]["moduleCount"]
        required = min(len(available), max(2, -(-int(count) // 4)))
        ok = len(available) >= required
        print(f"  {'ok ' if ok else 'NO '} grade {grade:>2}: {len(available)} module types "
              f"available, {required} distinct required")
        if not ok:
            failures.append(f"grade {grade} demands more distinct types than exist")

    print()
    print("Teacher's grade window")
    print("-" * 60)
    for class_grade in (1, 6, 11):
        low = max(1, class_grade - WINDOW)
        high = min(MAX_GRADE, class_grade + WINDOW)
        print(f"  class of grade {class_grade:>2} may set {low}..{high}")
        if class_grade == 11 and low > 8:
            pass
    # The point of the window: an eleventh-grade class cannot be given easy work.
    low_11 = max(1, 11 - WINDOW)
    if low_11 < 10:
        failures.append(f"an 11th grade class can be given grade {low_11} work")
    else:
        print(f"  ok: an 11th grade class cannot be set easier than grade {low_11}")

    failures += check_builders()
    if not failures:
        print("  ok: every module has a builder and every builder has a module")

    print()
    if failures:
        for failure in failures:
            print(f"  - {failure}")
        print(f"\nFAILED: {len(failures)} problem(s).")
        return 1
    print("All obstacle checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
