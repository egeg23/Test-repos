#!/usr/bin/env python3
"""Every purchasable must do something.

This is the check that should have existed from the first commit. Without it,
six of nine game passes, four of four consumables and four of seven ad rewards
were on sale, purchasable, granted -- and read by no line of code anywhere. The
grant ran, a counter went up, and nothing ever looked at it. Players would have
paid Robux and watched ads for effects that did not exist.

It is the worst possible class of bug in this project, and the easiest to
introduce: adding an item to the shop is one table entry, and wiring it up is a
different file. Nothing about the shop entry looks incomplete.

So, three rules, checked against the source:

  * Every pass id must be read by something other than the shop that lists it.
  * Every consumable a service writes must be read by some service.
  * Every ad reward must have an effect, and every effect must do more than
    write a counter nothing reads.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MONETIZATION = (ROOT / "src/shared/Config/Monetization.luau").read_text(encoding="utf-8")
SERVER = sorted((ROOT / "src/server").rglob("*.luau"))
CLIENT = sorted((ROOT / "src/client").rglob("*.luau"))

problems: list[str] = []


def ids(section: str) -> list[str]:
    start = MONETIZATION.find(f"Monetization.{section} = {{")
    if start < 0:
        raise SystemExit(f"check_monetization: could not find Monetization.{section}")
    depth = 0
    i = MONETIZATION.index("{", start)
    for j in range(i, len(MONETIZATION)):
        if MONETIZATION[j] == "{":
            depth += 1
        elif MONETIZATION[j] == "}":
            depth -= 1
            if depth == 0:
                return re.findall(r'id = "(\w+)"', MONETIZATION[i:j])
    raise SystemExit(f"check_monetization: Monetization.{section} is not brace-balanced")


# The shop itself lists everything, so a mention there is not a use. Same for the
# client, which draws the catalogue.
LISTERS = {"ShopService.luau", "ShopController.luau", "AdService.luau"}
server_text = {p.name: p.read_text(encoding="utf-8") for p in SERVER}
client_text = {p.name: p.read_text(encoding="utf-8") for p in CLIENT}


def used_by(needle: str, skip: set[str]) -> list[str]:
    hits = []
    for name, text in list(server_text.items()) + list(client_text.items()):
        if name in skip:
            continue
        if needle in text:
            hits.append(name)
    return hits


# --- passes --------------------------------------------------------------------

# A pass is "read" only by an ownership check. Matching the bare id string was
# not enough: the achievement panel lists an unrelated perk called lessonSlots,
# and that coincidence made a dead pass look wired up -- which is exactly the
# bug this file exists to catch, so it is worth being strict about.
def pass_checks(pass_id: str) -> list[str]:
    patterns = [
        rf'ownsPass\([^)]*"{pass_id}"',
        rf"\bownedPasses\.{pass_id}\b",
        rf"\bpasses\.{pass_id}\b",
        rf'\bownedPasses\["{pass_id}"\]',
        rf'\bpasses\["{pass_id}"\]',
    ]
    hits = []
    for name, text in list(server_text.items()) + list(client_text.items()):
        if name in LISTERS:
            continue
        if any(re.search(pattern, text) for pattern in patterns):
            hits.append(name)
    return hits


for pass_id in ids("Passes"):
    if not pass_checks(pass_id):
        problems.append(f"pass '{pass_id}' is sold but no ownership check reads it")

# --- consumables ---------------------------------------------------------------

written: set[str] = set()
for text in server_text.values():
    written |= set(re.findall(r'bump\(data\.consumables, "(\w+)"\)', text))
    written |= set(re.findall(r'data\.consumables\.(\w+) = ', text))

# A consumable must be *spent*, not merely looked at. Reading a count and then
# doing nothing with it is what a half-finished feature looks like, and it is
# indistinguishable from a working one if the check only asks for a mention.
SPEND = [
    r"consumables\.{name} -= ",
    r"consumables\.{name} = \w[\w.]* - ",
    r"consumables\.{name} = [\w.]+ - ",
    r'consumables\["{name}"\] -= ',
]

for name in sorted(written):
    spenders = []
    for filename, text in server_text.items():
        if any(re.search(p.format(name=name), text) for p in SPEND):
            spenders.append(filename)
    if not spenders:
        problems.append(f"consumable '{name}' is granted but nothing spends it")

# --- ad rewards ----------------------------------------------------------------

ad_service = server_text.get("AdService.luau", "")
effects_block = re.search(
    r"local effects: \{ \[string\]: \(Player, Types\.ProfileData\) -> \(\) \} = \{(.*?)\n\}",
    ad_service,
    re.S,
)
if not effects_block:
    problems.append("could not read the ad effects table")
else:
    declared_effects = set(re.findall(r"^\t(\w+) = function", effects_block.group(1), re.M))
    for reward_id in ids("AdRewards"):
        if reward_id not in declared_effects:
            problems.append(f"ad reward '{reward_id}' has no effect and would grant nothing")

print(f"  {len(ids('Passes'))} passes, {len(ids('Products'))} products, "
      f"{len(ids('AdRewards'))} ad rewards, {len(written)} consumables")

if problems:
    for problem in problems:
        print(f"  FAIL: {problem}")
    sys.exit(1)
print("Every purchasable does something.")
