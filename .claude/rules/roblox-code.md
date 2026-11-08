---
paths:
  - "roblox-*/src/**/*.luau"
  - "roblox-*/src/**/*.lua"
  - "roblox-*/tests/**/*.luau"
---

# Roblox / Luau Code Rules (DevUz)

- `--!strict` at the top of every module; public functions typed
- Server owns every number that matters (coins, inventory, theft, trades,
  purchases). Client code under `src/client` may only request through remotes
- Every remote handler: validate types, ranges, ownership, distance, cooldown;
  rate-limit per player; never `InvokeClient`
- Purchases only through an idempotent `MarketplaceService.ProcessReceipt`
- Paid random items: odds visible, gated by `PolicyService`
  (`ArePaidRandomItemsRestricted`); ads only where policy and age allow
- Player text shown to others goes through `TextService` filtering
- No player-facing string literals — use the game's `Strings.luau` keys in all
  supported languages; no tuning numbers inline — use `src/shared/Config`
- `task.wait/spawn/defer`, never `wait/spawn/delay`; disconnect connections;
  no per-frame `Instance.new`
- Before closing a story: `bash <game>/tools/check_all.sh` passes (Luau lint,
  unit tests, requires, calls, hardcoded strings, monetization, anti-cheat,
  economy simulation)
- Consult `roblox-specialist` for remotes, saved data, monetization and policy
