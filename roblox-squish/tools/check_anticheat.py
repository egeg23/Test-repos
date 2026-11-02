#!/usr/bin/env python3
"""The server-authority rules theft and coins depend on.

Every one of these is a single line in a service that a refactor could drop
while every test kept passing, because the tests run the shared rules, not the
services that are supposed to call them. If the call goes, the rule is still
correct and simply no longer consulted. So this reads the services and checks
the calls are there:

  * coins change in exactly one module, and never from a value a client sent;
  * a steal completes only after a hold the server measured, at the shelf,
    against a robbable victim, never on a favourite;
  * a carrier moves at the speed the server set, and a speed violation sends
    the squish home;
  * delivery happens only inside the thief's own walls;
  * merging goes through the shared merge rule.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
problems: list[str] = []


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def body(text: str, signature: str) -> str:
    start = text.find(signature)
    if start < 0:
        problems.append(f"could not find {signature!r}")
        return ""
    end = re.search(r"\n(end|\})\n", text[start:])
    return text[start : start + end.start()] if end else text[start:]


def strip_comments(text: str) -> str:
    return re.sub(r"--.*", "", text)


# --- coins --------------------------------------------------------------------

COIN_WRITE = re.compile(r"\b(?:data|\w+Data)\.coins\s*(?:[-+*/]?=)(?!=)")
for path in sorted((SRC / "server").rglob("*.luau")):
    rel = path.relative_to(ROOT).as_posix()
    if rel == "src/server/Services/SquishService.luau" or rel.endswith("DataService.luau"):
        continue
    for number, line in enumerate(strip_comments(path.read_text(encoding="utf-8")).split("\n"), 1):
        if COIN_WRITE.search(line):
            problems.append(f"{rel}:{number}: coins written outside SquishService")

squish = read("src/server/Services/SquishService.luau")
on_action = body(squish, "local function onBaseAction")
if re.search(r"body\.(coins|amount|income|reward)", on_action):
    problems.append("SquishService.onBaseAction reads a coin amount from the client")

for path in sorted((SRC / "client").rglob("*.luau")):
    rel = path.relative_to(ROOT).as_posix()
    text = strip_comments(path.read_text(encoding="utf-8"))
    for call in re.finditer(r"FireServer\(([^\n]*)", text):
        if re.search(r"\b(coins|amount|income|reward|tier|rarity)\s*=", call.group(1)):
            problems.append(f"{rel}: a client sends a value the server must compute ({call.group(1).strip()[:50]})")

squeeze = body(squish, "function SquishService.squeeze")
for needle, why in (
    ("SqueezeCooldown", "the per-squish squeeze cooldown"),
    ("RateLimiter.consume", "the per-player squeeze rate limit"),
    ("slotOf(data, uid) == nil", "the check that the squish is the clicker's own and on a shelf"),
):
    if needle not in squeeze:
        problems.append(f"SquishService.squeeze lost {why}")

merge = body(squish, "local function findMergePartner")
if "Economy.canMerge" not in merge:
    problems.append("merging no longer goes through Economy.canMerge")

# --- theft ----------------------------------------------------------------------

steal = read("src/server/Services/StealService.luau")
pickup = body(steal, "local function tryPickup")
for needle, why in (
    ("Steal.holdSeconds", "the server-measured hold time"),
    ("Steal.PromptDistance", "the distance check to the shelf"),
    ("Steal.canBeRobbed", "the victim rules"),
    ("Steal.favourites", "the favourites protection"),
    ("thiefReady", "the thief's cooldown and free-slot check"),
    ("thief == owner", "the self-theft refusal"),
):
    if needle not in pickup:
        problems.append(f"StealService.tryPickup lost {why} ({needle})")

begin = body(steal, "local function beginCarry")
if not re.search(r"MovementGuard\.setSpeed\(thief,\s*Steal\.carrySpeed", begin):
    problems.append("beginCarry no longer sets the carry speed through MovementGuard")
if "MovementGuard.setCarrying(thief, true)" not in begin:
    problems.append("beginCarry no longer marks the carrier for the height check")

start = body(steal, "function StealService.start")
violation = re.search(r"MovementGuard\.onViolation\(function([\s\S]*?)\n\tend\)", start)
if violation is None or "cancelCarry(carry)" not in violation.group(1):
    problems.append("a movement violation no longer sends the carried squish home")

step = body(steal, "local function step")
if not re.search(r"Base\.insideWalls\([^)]*\)\s*then\s*deliver\(carry\)", step):
    problems.append("delivery is no longer gated on the thief being inside their own walls")
if "Steal.CarryTimeoutSeconds" not in step:
    problems.append("the carry timeout is gone")
deliver_calls = [m.start() for m in re.finditer(r"\bdeliver\(carry\)", strip_comments(steal))]
if len(deliver_calls) != 1:
    problems.append(f"deliver(carry) is called from {len(deliver_calls)} places; it must only be reached from the walls check")

deliver = body(steal, "local function deliver")
if "Steal.ReturnHomeChance" not in deliver:
    problems.append("the return-home roll is gone from delivery")
if "ShieldAfterTheftSeconds" not in deliver or "lossesToday += 1" not in deliver:
    problems.append("delivery no longer shields the victim and counts the loss")

guard = read("src/server/Services/MovementGuard.luau")
sample = body(guard, "local function sample")
if "track.expectedSpeed" not in sample:
    problems.append("MovementGuard compares against something other than the speed the server set")
if re.search(r"Humanoid\)?\.WalkSpeed|humanoid\.WalkSpeed", sample):
    problems.append("MovementGuard reads WalkSpeed from the humanoid, which a client controls")

if problems:
    for problem in problems:
        print(f"  - {problem}")
    print(f"\nFAILED: {len(problems)} anti-cheat problem(s).")
    sys.exit(1)

print("Coins are server-only; theft is held, checked, speed-limited and delivered by the server.")
