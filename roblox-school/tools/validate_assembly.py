#!/usr/bin/env python3
"""Checks assembly tasks against the shared component catalogue.

Two failures here are silent rather than loud, which is why they are worth a
tool. A task whose answer is not in its own palette is unsolvable but looks
fine. A task whose palette holds only the pieces it needs solves itself by
elimination, which is also not obviously wrong to read.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS = ROOT / "content/assembly"
COMPONENTS = ROOT / "src/shared/Config/Components.luau"
AUTHORING = ROOT / "src/shared/Config/Authoring.luau"


def _scalar(path: Path, prefix: str, name: str) -> int:
    match = re.search(
        rf"^{prefix}\.{name}\s*=\s*(\d+)$", path.read_text(encoding="utf-8"), re.MULTILINE
    )
    if not match:
        raise SystemExit(f"validate_assembly: could not read {prefix}.{name}")
    return int(match.group(1))


MIN_SLOTS = _scalar(COMPONENTS, "Components", "MinSlots")
MAX_SLOTS = _scalar(COMPONENTS, "Components", "MaxSlots")
MIN_DISTRACTORS = _scalar(COMPONENTS, "Components", "MinDistractors")
MIN_EXPLANATION = _scalar(AUTHORING, "Authoring", "MinExplanationChars")
MAX_EXPLANATION = _scalar(AUTHORING, "Authoring", "MaxExplanationChars")


def catalogue() -> dict[str, str]:
    text = COMPONENTS.read_text(encoding="utf-8")
    found = re.findall(r'\{\s*id\s*=\s*"(\w+)",\s*subject\s*=\s*"(\w+)"', text)
    if not found:
        raise SystemExit("validate_assembly: could not read the component catalogue")
    return {name: subject for name, subject in found}


def validate(path: Path, components: dict[str, str]) -> tuple[list[str], int]:
    where = path.relative_to(ROOT).as_posix()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{where}: invalid JSON: {exc}"], 0

    errors: list[str] = []
    subject = payload.get("subject")
    if payload.get("locale") != path.parent.name:
        errors.append(f"{where}: locale does not match its directory")

    seen: set[str] = set()
    tasks = payload.get("tasks", [])
    for task in tasks:
        tid = task.get("id", "<no id>")
        prefix = f"{where}: {tid}"
        if tid in seen:
            errors.append(f"{prefix}: duplicate id")
        seen.add(tid)

        slots = task.get("slots") or []
        answers = task.get("answers") or []
        palette = task.get("palette") or []

        if len(slots) != len(answers):
            errors.append(f"{prefix}: {len(slots)} slots but {len(answers)} answers")
            continue
        if not MIN_SLOTS <= len(slots) <= MAX_SLOTS:
            errors.append(
                f"{prefix}: {len(slots)} slots, allowed {MIN_SLOTS}..{MAX_SLOTS}"
            )
        if len(set(answers)) != len(answers):
            errors.append(f"{prefix}: the same piece answers two slots")

        for piece in set(answers) | set(palette):
            if piece not in components:
                errors.append(f"{prefix}: '{piece}' is not in the component catalogue")
            elif components[piece] != subject:
                errors.append(
                    f"{prefix}: '{piece}' belongs to {components[piece]}, not {subject}"
                )

        missing = [a for a in answers if a not in palette]
        if missing:
            errors.append(f"{prefix}: answer(s) {missing} are not in the palette — unsolvable")

        distractors = len(set(palette)) - len(set(answers))
        if distractors < MIN_DISTRACTORS:
            errors.append(
                f"{prefix}: only {distractors} spare pieces "
                f"(need {MIN_DISTRACTORS}) — it solves itself by elimination"
            )

        explanation = task.get("explanation", "")
        if not MIN_EXPLANATION <= len(explanation) <= MAX_EXPLANATION:
            errors.append(
                f"{prefix}: explanation is {len(explanation)} chars, "
                f"allowed {MIN_EXPLANATION}..{MAX_EXPLANATION}"
            )

        grade = task.get("grade")
        if not isinstance(grade, int) or not 1 <= grade <= 11:
            errors.append(f"{prefix}: grade must be 1..11, got {grade!r}")

    return errors, len(tasks)


def main() -> int:
    files = sorted(TASKS.rglob("*.json"))
    if not files:
        print(f"No assembly tasks under {TASKS.relative_to(ROOT)}")
        return 1

    components = catalogue()
    all_errors: list[str] = []
    total = 0
    for path in files:
        errors, count = validate(path, components)
        all_errors.extend(errors)
        total += count
        print(f"{'FAIL' if errors else '  ok':>4}  "
              f"{path.relative_to(ROOT).as_posix():<40} {count:>4} tasks")

    print()
    if all_errors:
        for error in all_errors:
            print(f"  - {error}")
        print(f"\nFAILED: {len(all_errors)} problem(s).")
        return 1
    print(f"All {total} tasks across {len(files)} file(s) pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
