---
name: develop-godot
description: "Godot 4.7 game development in GDScript, 2D and 3D: scenes, nodes, TileMapLayer, CharacterBody2D/3D, Jolt physics, UI, input, animation, headless checks and tests. Use for any Godot, GDScript or .tscn/.gd work, platformers, top-down and 3D games, or turning an imagine context lake into a playable slice."
metadata:
  recommendedRole: build
  aliases: develop-godot-2d, develop-godot-3d, godot-2d-game-dev, godot-3d-game-dev, godot-2d, godot-3d, gdscript
  cliDependencies:
    required: [python3, agentctl, rg]
    optional: [godot]
---
# Develop Godot 4.7

Typed GDScript for Godot 4.7 (2D and 3D), verified headless. Docs are offline; the Godot binary is `godot` (`~/.local/bin/godot`, 4.7.2).

## Inputs

| Input | Required | Notes |
|---|---|---|
| Task or PRD | yes | Feature, bug, or vertical slice. |
| Project path | no | Directory holding `project.godot`. None found: create one only when the task says so. |
| Imagine lake | no | Output of the `imagine` skill. Read-only input; never required, never written to. See [references/imagine-intake.md](references/imagine-intake.md). |

## Documentation lookup order (offline first)

Catalog: `~/.agents/kb/offline-reference/godot/` (Godot 4.7). Page path is the docs-relative path plus `.md`, for example `classes/class_tilemaplayer.md`.

1. `agentctl docs search '<focused query>' --db ~/.agents/.cache/offline-docs.sqlite --json`. Open only the best hit. A missing-index result means go to step 2.
2. `~/.agents/kb/offline-reference/godot/llm-index.md` (chooser), then the page. Topic routing: [references/2d.md](references/2d.md), [references/3d.md](references/3d.md).
3. Read the section you need with `rg -n` and `sed -n`, never a whole class page.
4. Official site `https://docs.godotengine.org/en/4.7/` only when the catalog lacks the page; say so in the reply.

Examples to copy structure from (outside the repo): `~/.local/share/godot/examples/{2d-platformer,3d-character}/` (index README there) and the official demos in `~/.local/share/godot/demo-projects/`.

## Workflow

1. **Detect.** Find `project.godot`; read `config/features` for the engine version and `physics/3d/physics_engine`. A project older than 4.7 keeps its version idioms unless the task is an upgrade (`tutorials/migrating/upgrading_to_godot_4.{3,4,5,6,7}.md`).
2. **Plan the model before code.** Scene tree and node types, collision layers and masks (name them in project settings), input actions, signals (up) and calls (down), data as Resources. For a lake, derive this from the lake first.
3. **Slice first.** One playable path end to end (player, one room or level, one interaction, win or fail) before breadth.
4. **Write typed GDScript.** Rules in [references/gdscript-core.md](references/gdscript-core.md); layout in [references/project-conventions.md](references/project-conventions.md).
5. **Verify.** `python3 ~/.agents/skills/develop-godot/scripts/check_project.py --path <project> [--tests res://tests/run_tests.gd] [--json]`. Details and exit codes: [references/verification.md](references/verification.md). Fix until `status` is `ok`.
6. **Report** what ran and what did not. A `blocked` status is not verification.

## Hard rules

- Check version-sensitive APIs in [references/version-gotchas.md](references/version-gotchas.md) before using them. Do not use `TileMap` (use one `TileMapLayer` per layer) or `ParallaxBackground` (use `Parallax2D`).
- Never hand-author or delete `.uid` files; the editor and `--import` generate them. Do not hand-write `uid://` values in `.tscn`/`.tres`.
- Ignore `.godot/` in version control. Keep `.import` and `.uid` files tracked (see gotchas for what is unverified).
- Headless means no editor: no `EditorPlugin`, no `@tool` side effects at runtime, no dialogs. Unknown CLI flags fail silently, so check the exit code and the output.
- `move_and_slide()` takes velocity in units per second; do not multiply by delta; call it from `_physics_process`.
- Do not claim a scene runs because it parses. Parse checks prove syntax only.
- Edit `.tscn` by hand only for small, reviewed changes; prefer building nodes in code or a SceneTree test for structure that must be exact.

## Factory and headless workers

`AGENTCTL_FACTORY=1`: ask no questions, no web, no browser. Leave artifacts on disk and finish with the worker `report.json` (`status`, `summary`, `artifacts`, `blockers`, `next_hint`; contract in `~/.agents/kb/implementation/How-to-run-the-dark-factory.md`).

- The allowlist includes `Bash(python3:*)`, so `check_project.py` runs inside a worker. On `blocked` (or a denied command), do not retry or work around it: set `report.json` `status` to blocked, put the script's summary under `blockers`, and the exact command in `next_hint`. Never claim verification without an `ok`.
- Never write git. The engine commits.
- Docs come from the offline catalog only.

## Refresh the docs catalog

Follow the Refresh section of `~/.agents/kb/offline-reference/godot/README.md`: `sync-godot-docs.py --version 4.7` with `--crawl --cache-dir ~/.local/share/godot/docs-src/<date>/html` or `--zip <file|url>`, then the `agentctl docs index` run over all catalogs. Never run the shared compactor on `godot/`.

## References

- [gdscript-core.md](references/gdscript-core.md): language and tree rules.
- [2d.md](references/2d.md), [3d.md](references/3d.md): topic to catalog page.
- [version-gotchas.md](references/version-gotchas.md): 4.x changes as do and don't.
- [verification.md](references/verification.md): check script, SceneTree tests, blocked handling.
- [project-conventions.md](references/project-conventions.md): layout, naming, `.gitignore`.
- [imagine-intake.md](references/imagine-intake.md): optional context lake to Godot work.
