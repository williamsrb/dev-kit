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
- A slot placed last in `pipeline` also extends the `synthesis` phase `slots` list; `tests/test_guide.py` `test_phase_range_equals_slot_range` names the last slot of the phase.
- A step that scans the checkout (`enonic.security`) treats `ctx.source` as optional input: skip the source-based kinds with `ctx.record_skip` and name them in the output. Share regexes with `check` through a module in `extractkit_cli/` (`credentials.py`), so the step and the gate cannot disagree.
- Read-only regression on a copy of a CI sidecar: set `source.path` in the copy's `MANIFEST.yaml` to the local export of the job's commit, or every `Evidence:` ref fails to resolve.
- Slot wiring list (2026-10, five slots added): `pipeline` position, `optional_slots`, exactly one phase's `slots`, `adapters: null` in `core.yaml` and `php.yaml`, the binding in `enonic.yaml`, and `registry._load()`. `doctor` fails a slot in no phase. Place a new synthesis slot before `report.security` so the phase's last slot, which `test_guide` names, does not move; a new static slot moves the `--until static` row count in `tests/test_guide.py`.
- `tests/test_docs.py` requires a `## <slot>` heading in `docs/steps.md` and the slot name in `docs/cli.md` for every core slot, so the full suite fails until the docs are written.
- A step with no fixed output (`enonic.capability_bundles`) sets `produces = ()`: `progress.step_complete` then counts it done and `status` stops suggesting it.
- A boolean flag that an optional step needs (`--baseline`): `cli._add_cms_flags`, `runner._context_from_args` `cms`, `guide.BOOLEAN_FLAGS` and `CARRY_FLAGS`, and for headless the `_cms()` flag list. The step returns silently when the flag is off, so a default run writes nothing and records no skip.
- `scope.iter_files` skips any folder whose `MANIFEST.yaml` carries the extract-manifest kind (the exact value is in `scope.iter_files`): a sidecar left under the checkout (`.tmp/extract/<run>`) otherwise feeds its generated OpenAPI and docs into every scan (caller scan, docs harvest).
- A module `steps/enonic/oracle.py` and a data folder `steps/enonic/oracle/` (the Node loader) coexist as long as the folder has no `__init__.py`.
