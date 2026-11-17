# GDScript core (Godot 4.7)

Docs: `tutorials/scripting/gdscript/gdscript_basics.md`, `static_typing.md`, `gdscript_exports.md`, `gdscript_styleguide.md`, `warning_system.md`.

## Typing

- Type every variable, parameter and return: `var speed: float = 200.0`, `func hit(dmg: int) -> void`. Use `:=` only when the type is obvious from the right side.
- Typed collections: `Array[Enemy]`, and `Dictionary[String, int]` (typed dictionaries, 4.4).
- Set `debug/gdscript/warnings/untyped_declaration` to warn (value 1, as the examples do) so untyped declarations surface. Do not blanket `@warning_ignore`.

## Tree and lifecycle

- Order: `_enter_tree`, `_ready` (children ready before parent), then per frame `_process(delta)` and per physics tick `_physics_process(delta)`.
- Physics bodies, `move_and_slide()`, forces: `_physics_process`. Visuals and UI: `_process`. Input handlers: `_unhandled_input` for gameplay so UI can consume events first.
- `@onready var x: Sprite2D = $Sprite2D` or `%UniqueName` for scene-unique nodes. Do not cache paths across scene instances.
- `queue_free()` is deferred and safe during a signal. After it, null checks use `is_instance_valid()`.

## Signals and calls

- Signals up, calls down. A child emits; its parent connects. Siblings talk through the parent or a shared Resource.
- `signal died(by: Node)`, connect with `died.connect(_on_died)`; `await some_signal` for one-shot waits.
- Disconnect dynamic connections you made to nodes that outlive the listener.

## Exports and data

- `@export var stats: EnemyStats` with a custom `Resource` (`class_name EnemyStats extends Resource`) for data. Data in Resources, behavior in nodes.
- `@export_range`, `@export_enum`, `@export_group`. `@export_file` and `@export_dir` are editor path pickers; `@export_tool_button("Label") var b: Callable` needs `@tool` on the script.
- `Resource.duplicate()` is shallow for sub-resources; use `duplicate_deep()` for an independent copy (see gotchas).

## Loading

- `preload("res://x.tscn")` resolves at compile time, for constant paths.
- `load()` is **synchronous and blocks** the main thread. For big resources use `ResourceLoader.load_threaded_request(path)`, poll `load_threaded_get_status(path)`, then `load_threaded_get(path)`. Docs: `tutorials/io/background_loading.md`.
- Switch scenes with `get_tree().change_scene_to_packed()` or `change_scene_to_file()`, not by freeing the root.

## Input

- Define actions in the InputMap, never hard-code keys: `Input.get_vector("left","right","up","down")`, `Input.is_action_just_pressed("jump")`. Docs: `tutorials/inputs/inputevent.md`, `input_examples.md`.
- Headless tests inject events with `Input.parse_input_event()` or `Input.action_press("jump")`; remember to `action_release`.

## Language features worth knowing

- `@abstract` classes and methods, and variadic parameters (`...args`), exist in 4.5+. Docs: `gdscript_basics.md`.
- `class_name` registers a global type; keep one per file. Use `static func` and `const` for pure helpers.
- `match` for state machines; an `enum State { IDLE, RUN }` plus a `match` is enough before reaching for node-based FSMs.
- Autoloads: sparingly, for true globals (settings, save service, event bus). Docs: `tutorials/scripting/singletons_autoload.md`, `tutorials/best_practices/autoloads_versus_regular_nodes.md`.

## Pausing and timers

`get_tree().create_timer(s).timeout` for one-shot delays. `process_mode` controls behavior while paused (`tutorials/scripting/pausing_games.md`).
