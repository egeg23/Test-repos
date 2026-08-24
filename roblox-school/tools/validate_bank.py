#!/usr/bin/env python3
"""Enforces the question authoring rules on every bank file.

The goal of the bank is understanding, not recall, and most of what ruins that
is invisible in any single question. Two checks here are about the bank as a
whole: whether the correct answer tends to be the longest option, and whether it
tends to sit in the same slot. Children find both patterns fast, and once they
do the test measures pattern-spotting instead of learning.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BANKS = ROOT / "content/banks"

MAX_STEM_CHARS = 120
REQUIRED_OPTIONS = 4
MIN_EXPLANATION_CHARS = 20
# An option this much longer than the average is a giveaway on sight.
MAX_OPTION_LENGTH_RATIO = 1.8
# Share of questions whose correct answer is the longest option, or sits in any
# one slot. Uniform would be 25%; these are the points where a pattern emerges.
MAX_LONGEST_CORRECT_SHARE = 0.40
MAX_SLOT_SHARE = 0.40


def validate_question(question: dict, seen_ids: set[str], where: str) -> list[str]:
    errors = []
    qid = question.get("id", "<missing id>")
    prefix = f"{where}: {qid}"

    if not isinstance(qid, str) or not qid:
        errors.append(f"{prefix}: missing id")
    elif qid in seen_ids:
        errors.append(f"{prefix}: duplicate id")
    else:
        seen_ids.add(qid)

    grade = question.get("grade")
    if not isinstance(grade, int) or not 1 <= grade <= 11:
        errors.append(f"{prefix}: grade must be 1..11, got {grade!r}")

    stem = question.get("stem", "")
    if not isinstance(stem, str) or not stem.strip():
        errors.append(f"{prefix}: empty stem")
    elif len(stem) > MAX_STEM_CHARS:
        errors.append(f"{prefix}: stem is {len(stem)} chars, limit {MAX_STEM_CHARS}")

    options = question.get("options")
    if not isinstance(options, list) or len(options) != REQUIRED_OPTIONS:
        errors.append(f"{prefix}: needs exactly {REQUIRED_OPTIONS} options")
        return errors

    if any(not isinstance(o, str) or not o.strip() for o in options):
        errors.append(f"{prefix}: an option is empty")
    if len({o.strip().lower() for o in options}) != REQUIRED_OPTIONS:
        errors.append(f"{prefix}: options are not distinct")

    lengths = [len(o) for o in options]
    mean = sum(lengths) / len(lengths)
    if mean > 0 and max(lengths) / mean > MAX_OPTION_LENGTH_RATIO:
        errors.append(
            f"{prefix}: option lengths {lengths} are lopsided; "
            f"the long one reads as the answer"
        )

    answer = question.get("answer")
    if not isinstance(answer, int) or not 1 <= answer <= REQUIRED_OPTIONS:
        errors.append(f"{prefix}: answer must be 1..{REQUIRED_OPTIONS}, got {answer!r}")

    explanation = question.get("explanation", "")
    if not isinstance(explanation, str) or len(explanation.strip()) < MIN_EXPLANATION_CHARS:
        errors.append(
            f"{prefix}: explanation is the part that teaches; "
            f"needs at least {MIN_EXPLANATION_CHARS} chars"
        )

    return errors


def validate_bank(path: Path) -> tuple[list[str], int]:
    errors: list[str] = []
    where = path.relative_to(ROOT).as_posix()

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{where}: invalid JSON: {exc}"], 0

    for field in ("subject", "locale", "questions"):
        if field not in payload:
            errors.append(f"{where}: missing '{field}'")
    if errors:
        return errors, 0

    if payload["locale"] != path.parent.name:
        errors.append(
            f"{where}: locale '{payload['locale']}' does not match directory "
            f"'{path.parent.name}'"
        )

    questions = payload["questions"]
    seen_ids: set[str] = set()
    longest_correct = 0
    slots: Counter[int] = Counter()

    for question in questions:
        errors.extend(validate_question(question, seen_ids, where))
        options, answer = question.get("options"), question.get("answer")
        if isinstance(options, list) and isinstance(answer, int) and 1 <= answer <= len(options):
            slots[answer] += 1
            lengths = [len(o) for o in options]
            # Only a *uniquely* longest correct answer is a tell. Several options
            # tied at the same length give nothing away, so a tie is not counted.
            if lengths[answer - 1] == max(lengths) and lengths.count(max(lengths)) == 1:
                longest_correct += 1

    total = len(questions)
    if total >= 10:
        share = longest_correct / total
        if share > MAX_LONGEST_CORRECT_SHARE:
            errors.append(
                f"{where}: the correct answer is the longest option in {share:.0%} "
                f"of questions (limit {MAX_LONGEST_CORRECT_SHARE:.0%}) -- players "
                f"will learn to pick the long one"
            )
        for slot, count in sorted(slots.items()):
            if count / total > MAX_SLOT_SHARE:
                errors.append(
                    f"{where}: {count / total:.0%} of answers sit in slot {slot} "
                    f"(limit {MAX_SLOT_SHARE:.0%})"
                )

    return errors, total


def main() -> int:
    files = sorted(BANKS.rglob("*.json"))
    if not files:
        print(f"No bank files under {BANKS.relative_to(ROOT)}")
        return 1

    all_errors: list[str] = []
    total = 0
    for path in files:
        errors, count = validate_bank(path)
        all_errors.extend(errors)
        total += count
        status = "FAIL" if errors else "ok"
        print(f"{status:>4}  {path.relative_to(ROOT).as_posix():<44} {count:>4} questions")

    print()
    if all_errors:
        for error in all_errors:
            print(f"  - {error}")
        print(f"\nFAILED: {len(all_errors)} problem(s).")
        return 1

    print(f"All {total} questions across {len(files)} bank(s) pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
