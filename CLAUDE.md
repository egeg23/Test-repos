# Игры DevUz — Claude Code Game Studios

Решение владельца, 08.11.2026: «Для игр всегда используем Claude Code Game
Studios… разверни его для всех игровых проектов наших… Для роблокс».

- **Студия** — [Claude Code Game Studios](https://github.com/Donchitos/Claude-Code-Game-Studios)
  1.2.0 (MIT, `.claude/CCGS-LICENSE`): 49 агентов, 74 навыка (`/start`,
  `/adopt`, `/help`, `/design-system`, `/create-stories`, `/dev-story`,
  `/story-done`, `/code-review`, `/playtest-report`…), хуки и правила. Любая
  работа над игрой идёт через неё: дизайн — через навыки студии, код — через
  `/dev-story`, проверка — `/code-review` и `/story-done`.
- **Под Roblox дописано нами** (в шаблоне только Godot, Unity, Unreal):
  агент `roblox-specialist`, правило `.claude/rules/roblox-code.md`, движок
  `Roblox` в `resolve_code_root` и выборе специалиста
  (`.claude/hooks/yaml-helper.sh`), `docs/engine-reference/roblox/VERSION.md`,
  пути Roblox в правилах gameplay/network/ui/test/data. Обновляя студию до новой
  версии — перенести эти правки (поиск по «DevUz»).
- **Игры в репозитории**: `roblox-squish/` («Сквиш-фабрика», активная) и
  `roblox-school/`. Активная — `engine.code_root` в `project.yaml`; на время
  работы над другой — `project.local.yaml` (в git не идёт). `design/` и
  `production/` в корне — активной игры.
- **Проверка перед сдачей** — `bash <игра>/tools/check_all.sh` (Luau, тесты,
  монетизация и правила Roblox, античит, симуляция экономики).
- Бот на Python и остальное в корне к студии не относится; хуки и правила
  студии привязаны к путям игр и `design/`, `production/`.

---

# Claude Code Game Studios -- Game Studio Agent Architecture

Indie game development managed through 49 coordinated Claude Code subagents.
Each agent owns a specific domain, enforcing separation of concerns and quality.

## Technology Stack

- **Engine**: Roblox (live platform)
- **Language**: Luau (`--!strict`)
- **Version Control**: Git
- **Build System**: Rojo (`rojo build` / `rojo serve`), packages — Wally, tools — Rokit
- **Asset Pipeline**: Roblox asset ids; images and audio uploaded through Studio / Open Cloud

> **Note**: the engine specialist is `roblox-specialist` (DevUz addition).
> The Godot, Unity and Unreal agent sets that ship with the template are not
> used here.

## Project Structure

@.claude/docs/directory-structure.md

## Engine Version Reference

<!-- ENGINE-REFERENCE-IMPORT: the line below is engine-specific. /setup-engine
     rewrites it to @docs/engine-reference/<engine>/VERSION.md for the chosen
     engine, so a Unity or Unreal project stops loading the Godot reference every
     session. It defaults to Godot (the template's example engine); skills that
     need the pinned version read docs/engine-reference/<engine>/VERSION.md on
     demand regardless of this import. -->
@docs/engine-reference/roblox/VERSION.md


## Technical Preferences

`project.yaml` at the repo root is the primary config store — engine, specialists,
naming, platform, performance, modes. Skills resolve it via `resolve_config`
(see `.claude/docs/config-resolution.md`).

`.claude/docs/technical-preferences.md` is the **legacy fallback**, read on demand
when a key is absent from `project.yaml`. It is not imported here: before
`/setup-engine` runs it is almost entirely `[TO BE CONFIGURED]` placeholders, and
after it runs `project.yaml` holds the real values.

## Coordination Rules

@.claude/docs/coordination-rules.md

## Collaboration Protocol

**User-driven collaboration, not autonomous execution.**
Every task follows: **Question -> Options -> Decision -> Draft -> Approval**

- Agents MUST ask "May I write this to [filepath]?" before using Write/Edit tools
  (exempt: `active.md` appends, agent memory, a subagent's new file at the path
  its orchestrating skill named; see `.claude/rules/agent-memory.md`)
- Agents MUST show drafts or summaries before requesting approval
- Multi-file changes require explicit approval for the full changeset
- No commits without user instruction
- A skipped or dismissed question is not an answer: act on nothing, re-ask in
  plain text and wait
- Started outside this file's folder? Warn first: hooks, deny rules and the
  ask-first mode load only when Claude Code starts here

See `docs/COLLABORATIVE-DESIGN-PRINCIPLE.md` for full protocol and examples.

> **First session on an existing game?** The engine is already configured in
> `project.yaml`. Run `/adopt` (brownfield onboarding) once per game, then
> `/help` for the next step. `/start` is for a brand-new game.

## Coding Standards

@.claude/docs/coding-standards.md

## Context Management

Read `.claude/docs/context-management.md` on demand — it is a reference, not
session context. Two of its conventions are load-bearing and cited by name
elsewhere in the repo, so they are restated here rather than lost:

- **`production/session-state/active.md` is the session checkpoint.** The file is
  the memory, not the conversation. Read it first after any compaction, crash, or
  `/clear`.
- **Helpers in `.claude/scripts/` emit observations, never verdicts.** A script
  that scores or judges will eventually contradict a mode or override it cannot
  see. (Cited by `artifact-check.sh` and `adr-dep-graph.sh`.)
