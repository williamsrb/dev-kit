# Project conventions

Docs: `tutorials/best_practices/project_organization.md`, `scene_organization.md`, `data_preferences.md`, `version_control_systems.md`, `tutorials/scripting/gdscript/gdscript_styleguide.md`.

## Layout

```text
project.godot
scenes/        # .tscn by feature: player/, enemies/, levels/, ui/
scripts/       # only scripts not sitting beside their scene
resources/     # .tres data (stats, items, tilesets)
assets/        # art, audio, fonts (source files stay outside res:// if large)
autoload/      # global scripts registered in project settings
tests/         # run_tests.gd and helpers
```

Prefer each scene with its script in one feature folder over type-based folders.

## Naming

- Files and folders: `snake_case` (`player.tscn`, `enemy_stats.tres`). Classes and nodes: `PascalCase`. Functions, variables, signals: `snake_case`; constants and enum values: `CONSTANT_CASE`; private members prefixed `_`.
- Signals in past tense (`died`, `item_picked`). Input actions are verbs (`jump`, `move_left`).
- Name collision layers in Project Settings, Layer Names. Document each layer's meaning in the plan.

## Architecture

- Signals up, calls down. A scene works on its own when run with F6.
- Data in `Resource` subclasses, not in dictionaries or scene properties scattered over nodes.
- Autoloads only for globals that truly outlive scenes. Pass dependencies down instead of reaching for globals.
- One responsibility per node script; compose with child nodes before inheriting.

## `.gitignore`

```gitignore
.godot/
*.translation
```

This is the list for Godot 4.1+ (`tutorials/best_practices/version_control_systems.md`). Track `export_presets.cfg`: 4.1+ keeps credentials out of it. Track `*.import` and `*.uid` files with their assets and never edit them by hand. The editor can generate `.gitignore` and `.gitattributes` (Project, Version Control, Generate Version Control Metadata).
