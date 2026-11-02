#!/usr/bin/env python3
"""Everything sold does something, and every platform rule on selling holds.

Two kinds of failure this exists for, both silent:

  * A pass or product on sale that no code ever reads. Adding a shop entry is
    one line in Config; wiring it up is a different file. Nothing about the
    shop entry looks unfinished. (The school this game borrows from shipped six
    dead passes before a check like this existed.)

  * A policy gate that quietly stops gating. Ads shown to a child, a paid
    random box shown where paid random items are banned, coins sold for Robux.
    Each of these is a short line of code that a refactor can drop without
    breaking any test, and each costs far more than a bug.

The rules are read off the source rather than run, so each one names the line
it expects. Every rule was made to fail by removing what it looks for.
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


def section(text: str, header: str) -> str:
    start = text.find(header)
    if start < 0:
        raise SystemExit(f"check_monetization: could not find {header!r}")
    depth = 0
    # The table itself, not a `{ [string]: ... }` type annotation before it.
    i = text.index("= {", start) + 2
    for j in range(i, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[i:j]
    raise SystemExit(f"check_monetization: {header!r} is not brace-balanced")


def function_body(text: str, signature: str) -> str:
    start = text.find(signature)
    if start < 0:
        return ""
    end = text.find("\nend\n", start)
    return text[start:end]


monetization = read("src/shared/Config/Monetization.luau")
passes = re.findall(r'id = "(\w+)"', section(monetization, "Monetization.Passes = {"))
products_block = section(monetization, "Monetization.Products = {")
ads_block = section(monetization, "Monetization.AdRewards = {")
ad_ids = re.findall(r'id = "(\w+)"', ads_block)

server = {p.relative_to(ROOT).as_posix(): p.read_text(encoding="utf-8") for p in (SRC / "server").rglob("*.luau")}
client = {p.relative_to(ROOT).as_posix(): p.read_text(encoding="utf-8") for p in (SRC / "client").rglob("*.luau")}

# --- passes -----------------------------------------------------------------

LISTERS = {"src/server/Services/ShopService.luau", "src/client/Controllers/ShopController.luau"}
for pass_id in passes:
    pattern = re.compile(rf'ownsPass\([^)]*"{pass_id}"')
    users = [name for name, text in server.items() if name not in LISTERS and pattern.search(text)]
    if not users:
        problems.append(f'pass "{pass_id}" is sold but no server code checks ownsPass(..., "{pass_id}")')

# --- products ---------------------------------------------------------------

EFFECT_FIELDS = ("paidBox", "boostSeconds", "shieldSeconds")
for entry in re.findall(r"\{[^{}]*\}", products_block):
    match = re.search(r'id = "(\w+)"', entry)
    if not match:
        continue
    product_id = match.group(1)
    fields = [field for field in EFFECT_FIELDS if re.search(rf"\b{field}\s*=", entry)]
    if len(fields) != 1:
        problems.append(f'product "{product_id}" must have exactly one effect field of {EFFECT_FIELDS}, has {fields or "none"}')
    if re.search(r"\bcoins\s*=", entry):
        problems.append(f'product "{product_id}" sells coins: every coin box would become a paid random item')

shop = server.get("src/server/Services/ShopService.luau", "")
grant = function_body(shop, "local function grantProduct")
for field, reader in (("paidBox", "BoxService.grantPaid"), ("boostSeconds", "activeBoosts.paid"), ("shieldSeconds", "shieldUntil")):
    if f"product.{field}" not in grant or reader not in grant:
        problems.append(f"ShopService.grantProduct does not apply {field} through {reader}")
if "addCoins" in grant or ".coins" in grant:
    problems.append("ShopService.grantProduct touches coins: Robux must never buy coins")

squish = server.get("src/server/Services/SquishService.luau", "")
if "activeBoosts.paid" not in function_body(squish, "function SquishService.multiplier"):
    problems.append("the paid boost is granted but SquishService.multiplier never reads activeBoosts.paid")
if "activeBoosts.ad" not in function_body(squish, "function SquishService.multiplier"):
    problems.append("the ad boost is granted but SquishService.multiplier never reads activeBoosts.ad")

# --- paid random items --------------------------------------------------------

if "PolicyCache.paidRandomAllowed" not in grant:
    problems.append("the paid box grant does not re-check PolicyCache.paidRandomAllowed; a modified client could buy it where it is banned")
catalogue = function_body(shop, "local function catalogue")
if not re.search(r"paidBox == nil and not product\.boostsCoins\) or paidRandom", catalogue):
    problems.append("ShopService.catalogue no longer drops the paid box for players restricted from paid random items")
if not re.search(r"pass\.boostsCoins and not paidRandom", catalogue):
    problems.append("ShopService.catalogue shows coin multipliers to players restricted from paid random items")
prompt = function_body(shop, "local function onPromptPurchase")
if "paidRandomAllowed" not in prompt:
    problems.append("ShopService.onPromptPurchase prompts the paid box without the policy check")
boxes_ui = client.get("src/client/Controllers/BoxController.luau", "")
if not re.search(r"not box\.paid or paidAllowed", boxes_ui):
    problems.append("BoxController draws the paid box without the server's paidRandomAllowed answer")
if not re.search(r"oddsBlock\(frame, box\)", boxes_ui):
    problems.append("BoxController no longer prints the odds on every box card")
policy = server.get("src/server/Services/PolicyCache.luau", "")
if "ArePaidRandomItemsRestricted == false" not in policy:
    problems.append("PolicyCache must treat a missing ArePaidRandomItemsRestricted as restricted (fail closed)")
if "IsPaidItemTradingAllowed == true" not in policy:
    problems.append("PolicyCache must treat a missing IsPaidItemTradingAllowed as not allowed (fail closed)")
trade = server.get("src/server/Services/TradeService.luau", "")
if trade.count("PolicyCache.paidTradingAllowed(session.a) and PolicyCache.paidTradingAllowed(session.b)") < 2:
    problems.append("TradeService must pass both players' IsPaidItemTradingAllowed into every offer check")
for site in ("BoxService.luau", "TradeService.luau", "StealService.luau"):
    text = server.get(f"src/server/Services/{site}", "")
    for call in re.findall(r"SquishService\.give\(([^\n]*)\)", text):
        if call.count(",") < 5:
            problems.append(f"{site}: SquishService.give({call[:40]}...) drops the paid flag")
if "AreAdsAllowed == true" not in policy:
    problems.append("PolicyCache must treat a missing AreAdsAllowed as not allowed (fail closed)")

# --- ads ----------------------------------------------------------------------

ads = server.get("src/server/Services/AdService.luau", "")
effects = section(ads, "local effects:")
for ad_id in ad_ids:
    if not re.search(rf"\b{ad_id}\s*=\s*function", effects):
        problems.append(f'ad reward "{ad_id}" has no effect in AdService')
availability = function_body(ads, "function AdService.availability")
if not re.search(r"not AdService\.adsAllowed\(player\)\s+then\s+return \{\}", availability):
    problems.append("AdService.availability must return an empty list to players PolicyService does not allow ads")
can_watch = function_body(ads, "function AdService.canWatch")
if "adsAllowed" not in can_watch:
    problems.append("AdService.canWatch does not check adsAllowed")
request = function_body(ads, "local function onRequestAd")
if "ShowRewardedVideoAdAsync" not in request or "CreateAdRewardFromDevProductId" not in request:
    problems.append("ad rewards must be shown through CreateAdRewardFromDevProductId + ShowRewardedVideoAdAsync")
if re.search(r"effect\(|effects\[", request):
    problems.append("onRequestAd applies an effect itself; rewards may only arrive through ProcessReceipt")
if 'registerGrant("adReward"' not in ads:
    problems.append("ad rewards are not registered as receipt grants")

shop_ui = client.get("src/client/Controllers/ShopController.luau", "")
if not re.search(r"if #shop\.ads > 0 then", shop_ui):
    problems.append("ShopController must draw no ad section at all when the server sends no ads")

if problems:
    for problem in problems:
        print(f"  - {problem}")
    print(f"\nFAILED: {len(problems)} monetization problem(s).")
    sys.exit(1)

print(f"{len(passes)} passes, products and {len(ad_ids)} ad rewards wired; policy gates in place.")
