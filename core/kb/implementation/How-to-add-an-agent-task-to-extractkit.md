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
- An optional report-only task (`spec.review`, writes `reports/`, no `promote`) still touches: `tests/test_agent_tasks.py` (id set, order, `list_json_shape`, unknown-task message), `tests/test_check.py` `test_every_named_check_exists`, the FR-10 doc sweep (`docs/{llm,steps,cli,output,flow}.md`, `skills/extract-agentic`), and the diagrams that name optional tasks (`phases`, `sidecar-lineage`, `extractkit-flow`). Rebuild diagrams from `*.elements.json` with `excalidraw-cli create`, render with `render_preview.py --scale 1` (scale 1 keeps the current PNG size). The `.elements.json` files have no trailing newline.
- Share the `MANIFEST.yaml` source lookup via `check._manifest_source(out)`; `_spec_review_gaps` and `_business_gaps` both resolve `Evidence:` refs with it.
