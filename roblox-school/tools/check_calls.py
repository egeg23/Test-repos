#!/usr/bin/env python3
"""Every cross-module call must land on something that exists.

Luau's checker cannot follow a require in this project: requires are Roblox
instance paths, which no file-based tool resolves, so every imported module
degrades to an unknown and a call to ClassService.doesNotExist() passes without
comment. The gate on unknown globals catches a missing *local*; it cannot catch
a missing *member* of a module that does exist.

That is the blind spot the last review fell into from the other side: a
function vanished from LessonService and eighteen commits of green checks
followed. This resolves requires by path, collects what each module actually
defines, and checks every dotted call against it.

Only exports are checked -- `Module.name(` where Module is a required local.
Method calls on instances, tables built at run time and dynamic keys are out of
scope, and the checker says nothing about them rather than guessing.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"

REQUIRE = re.compile(r"^local (\w+) = require\(([\w.]+)\)", re.M)
DEFINITION = re.compile(r"^function (\w+)\.(\w+)\s*\(", re.M)
ASSIGNMENT = re.compile(r"^(\w+)\.(\w+)\s*=", re.M)
USE = re.compile(r"\b(\w+)\.(\w+)\b")

# Requires resolve through the Rojo tree, which maps these roots onto folders.
ROOTS = {
    "ReplicatedStorage.Shared": SRC / "shared",
    "script.Parent": None,  # the requiring file's own directory
    "script.Parent.Parent": None,  # its parent's directory
}


def resolve(path_text: str, from_file: Path) -> Path | None:
    """Turns `script.Parent.Foo` or `ReplicatedStorage.Shared.Config.Bar` into a file."""
    if path_text.startswith("ReplicatedStorage.Shared."):
        rel = path_text[len("ReplicatedStorage.Shared.") :].split(".")
        return SRC / "shared" / Path(*rel[:-1]) / f"{rel[-1]}.luau"
    if path_text.startswith("ReplicatedStorage.Packages."):
        return None  # third-party, not checked
    if path_text.startswith("script."):
        # `script` is the requiring ModuleScript itself, so `script.Parent` is the
        # folder it sits in and `script.Parent.Foo` is a sibling file. The first
        # version of this started one level too high, resolved nothing under
        # script.Parent, and passed 404 references while checking none of the
        # ones that mattered. Verified against a deliberately misspelt call.
        parts = path_text.split(".")[1:]
        here = from_file
        rest: list[str] = []
        for part in parts:
            if part == "Parent" and not rest:
                here = here.parent
            else:
                rest.append(part)
        if not rest:
            return None
        candidate = here / Path(*rest[:-1]) / f"{rest[-1]}.luau"
        return candidate if candidate.exists() else None
    return None


def exports_of(path: Path, cache: dict[Path, set[str] | None]) -> set[str] | None:
    """Names a module defines on its returned table, or None if unreadable."""
    if path in cache:
        return cache[path]
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        cache[path] = None
        return None
    table = re.search(r"^local (\w+) = \{\}", text, re.M)
    if not table:
        cache[path] = None
        return None
    name = table.group(1)
    names = {m.group(2) for m in DEFINITION.finditer(text) if m.group(1) == name}
    names |= {m.group(2) for m in ASSIGNMENT.finditer(text) if m.group(1) == name}
    # Modules that export types: `export type Foo` is used as Module.Foo in
    # annotations, which is a legitimate dotted reference.
    names |= set(re.findall(r"^export type (\w+)", text, re.M))
    cache[path] = names
    return names


def main() -> int:
    problems: list[str] = []
    checked = 0
    cache: dict[Path, set[str] | None] = {}

    for file in sorted(SRC.rglob("*.luau")):
        text = file.read_text(encoding="utf-8")
        locals_to_file: dict[str, Path] = {}
        for m in REQUIRE.finditer(text):
            target = resolve(m.group(2), file)
            if target is not None:
                locals_to_file[m.group(1)] = target

        # Strip comments and strings so a mention in prose is not a call.
        code = re.sub(r"--\[\[.*?\]\]", "", text, flags=re.S)
        code = re.sub(r"--.*", "", code)
        code = re.sub(r'"(?:\\.|[^"\\])*"', '""', code)
        code = re.sub(r"`(?:\\.|[^`\\])*`", "``", code)

        for m in USE.finditer(code):
            module, member = m.group(1), m.group(2)
            target = locals_to_file.get(module)
            if target is None:
                continue
            exports = exports_of(target, cache)
            if exports is None:
                continue
            checked += 1
            if member not in exports:
                line = code.count("\n", 0, m.start()) + 1
                rel = file.relative_to(ROOT)
                problems.append(
                    f"{rel}:{line}: {module}.{member} -- {target.relative_to(ROOT)} "
                    f"defines no such member"
                )

    print(f"  {checked} cross-module references checked")
    if problems:
        for p in sorted(set(problems)):
            print(f"  FAIL: {p}")
        return 1
    print("Every cross-module reference resolves.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
