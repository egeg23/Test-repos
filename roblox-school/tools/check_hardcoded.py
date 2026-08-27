#!/usr/bin/env python3
"""Catches display text written straight into the interface code.

Localisation is the kind of work that is done once and then quietly undone, one
convenient string at a time. Two checks:

  * No non-Latin text anywhere outside the strings table itself. This catches a
    Russian string reappearing in a controller, which is exactly how the first
    pass ended up needing to be done at all.

  * No literal assigned to a `.Text` or `.PlaceholderText` property. Those are
    the properties a player reads, and a literal in one is a string that will
    never be translated. Symbols and digits are allowed -- a close button that
    says × is not a translation problem.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"

# The strings table holds every translation; the locale list holds the names
# languages call themselves. Both are meant to contain other alphabets.
ALLOW_NON_LATIN = {"shared/Strings.luau", "shared/Config/Locales.luau"}

NON_LATIN = re.compile(r"[^\x00-\x7F]")
# A letter in any alphabet, to tell real text from punctuation and digits.
HAS_LETTER = re.compile(r"[^\W\d_]", re.UNICODE)
TEXT_LITERAL = re.compile(r"\.(Text|PlaceholderText)\s*=\s*\"([^\"]*)\"")



LITERAL_KEY = re.compile(r"""(?:L\.text|Strings\.get)\(\s*"([A-Za-z0-9_.]+)"\s*[,)]""")
INTERPOLATED_KEY = re.compile(r"""(?:L\.text|Strings\.get)\(\s*`([A-Za-z0-9_.]*)\{""")


def missing_keys() -> list[str]:
    """Every string key referenced in code has to exist in the table."""
    table = (ROOT / "src/shared/Strings.luau").read_text(encoding="utf-8")
    known = set(re.findall(r'\["([A-Za-z0-9_.]+)"\]\s*=', table))
    if not known:
        return ["could not read any keys out of Strings.luau"]

    found: list[str] = []
    for path in sorted(SRC.rglob("*.luau")):
        if path.name == "Strings.luau":
            continue
        relative = path.relative_to(ROOT)
        text = path.read_text(encoding="utf-8")
        for number, line in enumerate(text.split("\n"), 1):
            for key in LITERAL_KEY.findall(line):
                if key not in known:
                    found.append(f"{relative}:{number}: string key '{key}' is not in the table")
            # `subject.{id}` cannot be resolved, but its prefix can: if nothing
            # in the table starts with it, the whole family is missing.
            for prefix in INTERPOLATED_KEY.findall(line):
                if prefix and not any(key.startswith(prefix) for key in known):
                    found.append(
                        f"{relative}:{number}: no string key begins with '{prefix}'"
                    )
    return found

def main() -> int:
    problems: list[str] = []

    for path in sorted(SRC.rglob("*.luau")):
        relative = path.relative_to(SRC).as_posix()
        text = path.read_text(encoding="utf-8")

        if relative not in ALLOW_NON_LATIN:
            for number, line in enumerate(text.split("\n"), 1):
                found = NON_LATIN.findall(line)
                # Typographic punctuation used in layout is not display text.
                letters = [c for c in found if HAS_LETTER.match(c)]
                if letters:
                    problems.append(
                        f"{relative}:{number}: non-Latin text outside the strings "
                        f"table: {''.join(letters)[:24]}"
                    )

        for number, line in enumerate(text.split("\n"), 1):
            for _, literal in TEXT_LITERAL.findall(line):
                if HAS_LETTER.search(literal):
                    problems.append(
                        f"{relative}:{number}: literal assigned to a displayed "
                        f'property: "{literal[:40]}"'
                    )

    problems += missing_keys()

    if problems:
        for problem in problems:
            print(f"  - {problem}")
        print(f"\nFAILED: {len(problems)} localisation problem(s).")
        return 1

    print("No hardcoded display text, and every string key resolves.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
