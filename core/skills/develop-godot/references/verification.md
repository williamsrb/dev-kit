# Verification

## Run the check

```bash
python3 ~/.agents/skills/develop-godot/scripts/check_project.py --path DIR [--tests res://x.gd] [--godot BIN] [--json] [--timeout 120] [--no-boot]
```

Binary resolution: an explicit `--godot` is used alone (no fallback); otherwise `$GODOT`, `PATH`, then `~/.local/bin/godot`. The script probes `--headless --version` first.

JSON result: `{status, godot_version, project, steps[{id, status, seconds, errors}], summary}`.

| Exit | `status` | Meaning |
|---|---|---|
| 0 | `ok` | Every step passed. |
| 1 | `failed` | A step failed; read `steps[].errors`, fix, rerun. A missing `project.godot` fails with step `project`. |
| 2 | `blocked` | No binary, or the binary fails the version probe. Nothing was verified. |

Steps, in order: `import`, `parse`, `tests` (only with `--tests`), `boot` (main scene run with `--quit-after 120`). Step status is `ok`, `failed` or `skipped`; `boot` is skipped with a reason under `--no-boot` or when the project has no run/main_scene. `parse` loads every `*.gd` outside `.godot/` and `addons/` with a runtime loader, because `--check-only` per file false-fails on autoload names.

Rules:
- Run it after every change set and before reporting. Fix until `ok`.
- `blocked` is never "passed". Report it as a blocker with the exact command.
- Factory worker: the allowlist includes `Bash(python3:*)`, so the script runs there. On `blocked`, write `report.json` with status blocked and the summary as the blocker (contract in `~/.agents/kb/implementation/How-to-run-the-dark-factory.md`). Never claim verification without an `ok`.
- Parse and import prove syntax and resource loading only. Gameplay claims need a test.

## Writing a SceneTree test

Copy the structure of `~/.local/share/godot/examples/2d-platformer/tests/run_tests.gd`: deferred start, a watchdog so a script error cannot hang the run, a counting `_check`, frames awaited between actions, exit 0 or 1.

```gdscript
extends SceneTree

var _failures: int = 0


func _initialize() -> void:
	create_timer(30.0, true, true).timeout.connect(func() -> void: quit(1))
	_run.call_deferred()


func _check(condition: bool, message: String) -> void:
	if not condition:
		_failures += 1
		printerr("  FAIL ", message)


func _frames(count: int) -> void:
	for i: int in count:
		await physics_frame


func _run() -> void:
	var main: Node = (load("res://scenes/main.tscn") as PackedScene).instantiate()
	root.add_child(main)
	await _frames(90)
	_check(main.get_node("Player").is_on_floor(), "player lands on the floor")
	quit(1 if _failures > 0 else 0)
```

- Autoloads are available under `root` (`root.get_node("/root/GameState")`).
- Use `Input.action_press` and `action_release` for input; assert on positions, signals and state.
- Keep tests in `res://tests/`, entry script `run_tests.gd`. No editor-only APIs.

## Manual commands (script unavailable)

```bash
godot --headless --path DIR --import --quit
godot --headless --path DIR --script res://tests/run_tests.gd
```

Read the exit code and scan output for `ERROR` and `SCRIPT ERROR`.
