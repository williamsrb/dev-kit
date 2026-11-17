---
id: how-to-add-an-agent-task-to-extractkit
when_skills: [run-plan, plan-implementation]
inputs: [extract-kit checkout, step spec]
outputs: [registered agent task, tests]
stop_if: [the kit would have to call a model]
read: whole
prose: caveman-lite
---

# How to add an agent task to extractkit

**Scope:** `extract-kit`
**Applies to:** `agent-tasks/`, `extractkit_cli/{agent_tasks,check,promote,progress,guide}.py` (measured 2026-10-01)

## Procedure

1. Create `agent-tasks/<id>/task.yaml` and `prompt.md`. The folder name equals `id`. Fields are in `schemas/agent-task.schema.json`: `after` (pipeline slot), `reads`, `writes`, `done` (marker paths) or `done_check`, `rerun` (argv tail as one string), `promote` (`{from, to}`), `checks`, `optional`.
2. The prompt opens with the Invariants block copied verbatim from `docs/llm.md` (a test compares). Only `{sidecar}`, `{source}`, `{profile}` and `{run_id}` are allowed; any other brace pair raises, so keep JSON and shell `${}` out of prompts.
3. Done state: a file marker when the file proves completion. When it cannot (`rules/review.md` exists from `rules.view`), add a predicate to `agent_tasks.DONE_CHECKS` and to the schema enum `done_check`.
4. Output validation: add a function to `check.py`, call it from `check_tree`, register it in `check.NAMED_CHECKS`, and validate only when the output exists (agent outputs are opt-in).
5. Promotion needs no code: `promote.cmd_promote` reads every task's `promote` rows through `agent_tasks.promotions(out)` under the existing git guard.
6. `agent next` returns required tasks only. An optional task (`optional: true`) is reached through `agent show <id>`.
7. Docs: `docs/steps.md` `## Agent tasks` (a Does / Writes / Skip block), `docs/output.md` tree and Promote list, `docs/llm.md` task table.

## Pitfalls

- A new phase renumbers every `[n/N]` label. Tests that hard-code them: `tests/test_guide.py`, `tests/test_next_promote.py`. `status`, `run`, `step` and `resume` all end with the agent suggestion while a required task is pending, so tests that expect `check` need `mock.patch("extractkit_cli.agent_tasks.pending", return_value=[])` or a written output.
- `guide.BOOLEAN_FLAGS` must list any new boolean flag (`--json`), or `guide.rewrite` swallows the next token when it rebuilds a `next` command.
- `progress` and `guide` import `agent_tasks` inside the function that needs it; `agent_tasks` imports both at module level.
- A command phase needs the phase `command` enum in `schemas/profile.schema.json` and a `runner.COMMAND_FIX` row, or `run --from <phase>` refuses without naming the command.
- A task with no `done` and no `done_check` is never done. Keep it `optional`.
- An optional report-only task (`spec.review`, writes `reports/`, no `promote`) still touches: `tests/test_agent_tasks.py` (id set, order, `list_json_shape`, unknown-task message), `tests/test_check.py` `test_every_named_check_exists`, the doc sweep (`docs/{llm,steps,cli,output,flow}.md`, `skills/extract-agentic`), and the diagrams that name optional tasks (`phases`, `sidecar-lineage`, `extractkit-flow`). Rebuild diagrams from `*.elements.json` with `excalidraw-cli create`, render with `render_preview.py --scale 1` (scale 1 keeps the current PNG size). The `.elements.json` files have no trailing newline.
- Share the `MANIFEST.yaml` source lookup via `check._manifest_source(out)`; `_spec_review_gaps` and `_business_gaps` both resolve `Evidence:` refs with it.
- Task ids allow `_` since 2026-10-02 (`context.live_config`); the schema pattern is `^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$`.
- A task that edits a shared file (`context/profile.yaml`: `context.exclude` writes `exclude`, `context.live_config` writes `live_config`) needs one `done_check` per key and a prompt that says "edit only your key". Order is by `after` slot index, so `agent next` names a task whose `after` is early (`inventory.integrations`) before the agent phase; `guide._pending_context_task` surfaces `context.*` tasks mid-pipeline. Other tasks stay out of mid-pipeline `next` blocks.
- Changing the Invariants block in `docs/llm.md` means rewriting it in every `agent-tasks/*/prompt.md`; replace the old block with the new one programmatically.
- A task whose input may never exist (no live harvest) must count as done when that input is absent, or the agent phase stays pending forever (`live_config_written`).
- `extractkit headless` runs agent tasks unattended: a prompt that says "stop and ask the operator" is overridden by `headless/preamble.md` (write `<sidecar>/reports/blockers/<id>.md`). Keep the task's stop rules in the prompt; headless adapts them. See `How-to-drive-extractkit-headless-and-test-it-with-a-fake-agent.md`.
- The Invariants block now says the CLI refuses to run from the kit and that `headless` is the one place that runs Serena, Graphify and graft; the six prompts carry that text.
- A task that must run after the `spec.kit` tasks (`business.reconcile`) uses `after: report.compat`, not `after: spec.kit`: `agent_tasks.ordered` sorts by (slot index, id), so `business.reconcile` under `spec.kit` sorts before `spec.capabilities`, and `progress._produced("spec-kit/specs/")` is true after the first spec. For a non-`context.*` task `after` only orders. `reads` on a directory documents the input and does not gate once the directory exists.
- A new required task makes every test that expects "no pending task" fail until `tests/support.write_agent_outputs` writes its `done` file. Count lists in `tests/test_agent_tasks.py` (ids, order, `list_json_shape`, `next` pending, the `status` agent row).
- Turning a `check` warning into an error (`_uncovered_entry_gaps`) fails `DomainGateTests.test_every_new_file_passes_when_valid` until `support.valid_capability_spec` names the fixture's service, task and cron.
- A task that runs once per capability (`per: capability`, 2026-10): put `{capability}` in `done` and `writes` (`domain/{capability}.md`); `agent_tasks.unit_done` and `is_done` fill it per id from `business/capabilities.json`, so no `done_check` is needed. Prompts may use `{capability}` and `{capability_title}`; the render error for an unknown brace pair lists them. Keep JSON examples out of the prompt (describe the shape in prose): `{ "a": 1 }` reads as a placeholder and raises. `agent show` without `--capability` renders the first pending unit, or `<capability>` placeholders while `business` has not written the list. `agent next` returns the first pending unit in `next.capability`.
- `rerun` is a string or a list of strings (`business` re-runs `step product.impeccable` then `step context.bundles`); `Task.rerun` is the first command, `Task.reruns` all of them, and headless runs each.
- An optional per-capability task (`rebuild.probe`) is never pending and never in a headless run: it is reached through `agent show <id> --capability <id>`, and shows `0/13` in `agent list`.
- A new required per-capability task needs `support.write_agent_outputs` to write its `done` file (`oracle.json` with `cases: []`), or every test that expects "nothing pending" fails.
- `check --capability <id>` scopes the per-capability gates; the gate that needs every capability written (`_uncovered_entry_gaps`) is skipped in that mode, or the first unit's check always fails.
- A new check gate that reads an agent output must stay silent when the output does not exist (`_oracle_gaps`), so a sidecar from before the task still passes `check`.
