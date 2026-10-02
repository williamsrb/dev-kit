---
id: how-to-add-an-optional-slot-to-extractkit
when_skills: [run-plan, plan-implementation]
inputs: [extract-kit checkout, step spec]
outputs: [registered optional slot, tests]
stop_if: [slot must be required in every profile]
read: whole
prose: caveman-lite
---

# How to add an optional pipeline slot to extractkit

**Scope:** `extract-kit`
**Applies to:** `profiles/*.yaml`, `extractkit_cli/{registry,runner,progress,guide}.py` (measured 2026-10-01)

## Procedure

1. Write `steps/<stack>/<name>.py` with `id`, `requires`, `produces`, `required = False`, `plan`, `run`, `check`. Write through `ctx.write_*`. Record a skip with `ctx.record_skip(step, reason, fix)` for a missing binary or input; never raise for those.
2. Register the class in `extractkit_cli/registry._load()`.
3. `profiles/core.yaml`: add the slot to `pipeline`, to one phase's `slots`, to `adapters` as `null`, and to `optional_slots`. Add `null` to `profiles/php.yaml` `adapters`, and the plugin id to `profiles/enonic.yaml`. `adapters` is a child-replace key, so a profile that extends `enonic` must omit the key.
4. `optional_slots` makes the runner drop the slot when unbound, and makes `status`, `resume` and `pipeline_state` ignore it. `status` prints `optional, not captured` and a pasteable `step <slot>` tip.
5. Done means every non-empty `produces` path exists, unless `progress.DISTINCTIVE` names the marker paths for that plugin id (`progress.step_complete`). List in `produces` only files the step always writes when it ran for real, or add a `DISTINCTIVE` entry.
6. New flag: add it to `cli._add_cms_flags`, to `runner._context_from_args` `cms`, and to `guide.CARRY_FLAGS`.
7. Tests: mock HTTP with `tests/test_cms.graphql_server`; mock `subprocess.run` for CLIs. Update `tests/test_guide.py` slot counts.

## Pitfalls

- A skip recorded under the plugin id replaces the slot's artifact row in `run` output. For a part of a step (not the whole step) use a distinct key such as `enonic.cms.configenv`.
- `maps.merge` rewrites the four map files. Anything another step wrote into them (for example `content-model.references`) must be read back and kept.
- `maps.merge` builds `route-map.json` from `project-map.json`, so `mapping` routes (only in `route-map.json` after `maps.normalize`) are dropped by it.
- `runner._execute` calls `ensure_self_ignore` only when `outtree.out_inside_source` is true (sidecar under `<source>/.extract/`). Keep that guard, or an external `--out` writes into the source.
- `ruff` ISC004: wrap multi-line implicit string concatenation inside tuples and lists in parentheses.
