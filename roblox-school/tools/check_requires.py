#!/usr/bin/env python3
"""Finds circular requires between modules.

Luau resolves a cycle by erroring at runtime, and only on the code path that
happens to load the two modules in the wrong order -- so a cycle can sit in a
build for weeks and then break in front of players. Nothing else in this
toolchain can see it: the syntax checker parses one file at a time, and the
Roblox instance paths in the requires are exactly what makes cross-file analysis
impossible for it.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"

# require(script.Parent.Foo) / require(ReplicatedStorage.Shared.Config.Bar)
REQUIRE = re.compile(r"require\(\s*([A-Za-z_][\w.]*)\s*\)")


def module_name(path: Path) -> str:
    if path.name in ("init.server.luau", "init.client.luau"):
        return path.parent.name
    return path.stem


def build_graph() -> tuple[dict[str, set[str]], dict[str, Path]]:
    files = sorted(SRC.rglob("*.luau"))
    known = {module_name(p): p for p in files}
    graph: dict[str, set[str]] = {name: set() for name in known}

    for path in files:
        name = module_name(path)
        for expression in REQUIRE.findall(path.read_text(encoding="utf-8")):
            target = expression.split(".")[-1]
            # Only edges between modules we actually own; Packages and services
            # resolved off `game` are leaves.
            if target in known and target != name:
                graph[name].add(target)
    return graph, known


def find_cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    cycles: list[list[str]] = []
    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(node: str) -> None:
        state[node] = 1
        stack.append(node)
        for neighbour in sorted(graph.get(node, ())):
            mark = state.get(neighbour, 0)
            if mark == 0:
                visit(neighbour)
            elif mark == 1:
                start = stack.index(neighbour)
                cycles.append(stack[start:] + [neighbour])
        stack.pop()
        state[node] = 2

    for node in sorted(graph):
        if state.get(node, 0) == 0:
            visit(node)
    return cycles


def main() -> int:
    graph, known = build_graph()
    cycles = find_cycles(graph)

    edges = sum(len(targets) for targets in graph.values())
    print(f"{len(known)} modules, {edges} internal requires")

    if cycles:
        print()
        for cycle in cycles:
            print("  cycle: " + " -> ".join(cycle))
        print(f"\nFAILED: {len(cycles)} circular require(s).")
        return 1

    print("No circular requires.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
