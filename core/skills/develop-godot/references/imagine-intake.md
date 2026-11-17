# Imagine intake (optional)

Use when the task names an `imagine` context lake (default location `~/.agents/imagine/<slug>/`). The lake is read-only input. This skill never requires one and never writes into it. Without a lake, work from the PRD alone.

## What to read, in order

1. `findings.md` game sections: Scenarios, Mechanics, Characters, Skills, Graphics, Maps, Quests, plus "Open assumptions". Start here.
2. `canon.json`: `axes` (era, tech ceilings), `regions`, `physics`, `tone`, `audience`, `market`, `rules[]`, `assumptions[]`. Also read `brief.md` for settled decisions.
3. `registry.json`: entities with ids; `registry.md` is the rendered view.
4. `plan.md` (the lake's own plan) and `story.md` (entities appear as `[[id]]`).

Files not in this list (research, risks) are background only.

## Mapping

| Lake | Godot work |
|---|---|
| Registry entity id (kebab-case) | Asset and node names in `snake_case`: `palm-well` becomes `palm_well.tscn`, `palm_well.gd`, resource `palm_well.tres`. Keep a one-line map `id -> res:// path` in `docs/lake_map.md` of the game project, so ids stay traceable. |
| `character` entities | One scene per character plus a stats `Resource`. Playable ones get a `CharacterBody2D/3D` scene. |
| `place` entities | Level or room scenes; `region` becomes a folder or tileset. |
| `concept`, `term` entities | Resources, enums, or UI strings; not nodes unless they behave. |
| `actor` entities | Not game content (production roles). Skip. |
| Canon `rules[]`, `physics`, `tone` | Design constraints: what mechanics are allowed, cost and limits of abilities, palette and audio mood. Quote the rule id in the plan, and enforce it in data validation where practical. |
| Canon `ceiling` on tech or era | Content filter: no asset, item or mechanic above the ceiling unless a rule allows it. |
| Findings Mechanics (core loop, progression, economy) | The systems list: one system per bullet, each with its input actions, signals, data resource and a testable acceptance line. |
| Findings Skills | Ability resources and the input actions that trigger them. |
| Findings Graphics | Art constraints: style, resolution, 2D or 3D choice, budget. Decides renderer and import settings. |
| Findings Maps and Quests | Level list and quest data resources. |
| Canon `assumptions[]` and findings "Open assumptions" | Defaults you may build on; list the ones you relied on in your report. |

## Order of work

1. Choose 2D or 3D from Graphics and Mechanics. Platform and medium are not a findings field: take them from `brief.md` and canon `market` and `audience`. If sources conflict, pick one and record it as a deviation.
2. Systems list and scene/node plan from Mechanics.
3. Vertical slice: one playable character, one place, the core loop once, one win or fail state, with a SceneTree test.
4. Add systems in the order the lake's `plan.md` gives; each with a test.
5. Content breadth (more places, characters, quests) last.

## Deviations

Never edit the lake. When the game must differ from canon or findings (technical limit, cut scope), record each deviation in the game project at `docs/deviations.md`: lake path, entity id or rule id, what the game does instead, why. Repeat the list in the final report so the operator can feed it back to the creative director.

## Factory compatibility

A lake path arrives as a plain input (PRD text or a task artifact path). Read it from disk; ask nothing. A missing or malformed lake file is a blocker to report, not a reason to invent content.
