# Roblox — Version Reference (DevUz)

| Field | Value |
|-------|-------|
| **Engine Version** | Roblox (live platform, no pinned engine version) |
| **Language** | Luau (`--!strict`) |
| **Tools (pinned per game)** | see `<game>/rokit.toml` — Rojo 7.7.0, Wally 0.3.2 in roblox-squish |
| **Packages (pinned per game)** | see `<game>/wally.toml` — ProfileStore 1.0.3 in roblox-squish |
| **Project Pinned** | 2026-11-08 |
| **Docs** | https://create.roblox.com/docs (API reference: /reference/engine) |

## Knowledge Gap Warning

Roblox ships engine and API changes every week and deprecates APIs without a
version bump. Treat any API recalled from memory as unverified until checked on
the Creator Docs page of that class. Prefer `task.*` over `wait/spawn/delay`,
`TextService:FilterStringAsync`, `PolicyService`, `MarketplaceService`
`ProcessReceipt`, `AdService`/rewarded ads only as the current docs describe.

## Policy pages to re-read before shipping monetization or UGC

- Paid random items and `PolicyService`: create.roblox.com/docs/production/monetization
- Advertising standards and ad eligibility: create.roblox.com/docs/production/promotion
- Experience Guidelines / content maturity labels: create.roblox.com/docs/production/promotion/experience-guidelines
- Text filtering: create.roblox.com/docs/ui/text-filtering

## Games in this repository

| Game | Code root (`engine.code_root`) | Checks |
|------|-------------------------------|--------|
| Сквиш-фабрика | `roblox-squish/src` | `bash roblox-squish/tools/check_all.sh` |
| roblox-school | `roblox-school/src` | see `roblox-school/README.md` |
