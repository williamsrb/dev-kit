# Roles → vendor model / effort

Guide for the operator and for orchestrators (`orchestrate`, `multitask-same-repo`)
that pick a model and effort when they spawn a subagent. Cells come from
`agentctl bench place` (2026-11-10, `~/.agents/benchmarks/placement.yaml`):
every benchmark in `latest.yaml` (Terminal-Bench 4.0, DeepSWE, Artificial Analysis free-tier
Intelligence Index v5) is converted to Terminal-Bench points, then each vendor gets the
cheapest config whose score minus one standard error clears the role's **absolute** floor in
`benchmarks/bands.yaml`. The floors are fixed points, not a fraction of the best model, so a
stronger model shipping does not raise the effort of any role. A few cells are hand
overrides of `place` (see Notes). Spawnable configs: `benchmarks/harness.yaml`. Refresh with
`agentctl bench collect`, then `agentctl bench place --markdown`.

Start every role at its cell and escalate only on evidence: if the review or the checks
fail, retry once one effort up on the same model and say so. The factory does exactly that and then parks; an interactive orchestrator may then move to the next model in the column.
Never start high "to be safe".

When you call a skill, read `metadata.recommendedRole` in that
skill’s `SKILL.md`, then pick the row below for the harness you are in.

**Evidence** in this harness means Jira/QA after delivery. It is not a role.

## Roles

Sorted cheapest/simplest first.

| Role | Codex | Claude | Cursor |
|---|---|---|---|
| `deterministic` | `gpt-6-luna` `medium` † | `claude-haiku-5-5` `low` † | `cursor-grok-4.7-low` † |
| `explore` | `gpt-6-luna` `high` † | `claude-haiku-5-5` `medium` † | `cursor-grok-4.7-low` † |
| `follow` | `gpt-6-luna` `high` † | `claude-haiku-5-5` `medium` † | `cursor-grok-4.7-low` † |
| `plan` | `gpt-6.1-terra` `xhigh` † | `claude-sonnet-5-5` `high` † | `cursor-grok-4.7-medium` † |
| `build` | `gpt-6.1-terra` `high` † | `claude-sonnet-5-5` `medium` † | `cursor-grok-4.7-medium` † |
| `impl-review` | `gpt-6.1-sol` `high` | `claude-opus-5-5` `medium` † | `cursor-grok-4.7-high` ‡ |
| `plan-review` | `gpt-6.1-sol` `high` | `claude-opus-5-5` `medium` † | `cursor-grok-4.7-high` ‡ |
| `task-owner` | `gpt-6.1-sol` `high` † | `claude-opus-5-5` `medium` † | `cursor-grok-4.7-high` ‡ |
| `quality-gate` | `gpt-6.1-sol` `xhigh` | `claude-opus-5-5` `high` † | `cursor-grok-4.7-xhigh` ‡ |

† Provisional: one evidence source (mostly Artificial Analysis) or an estimated cost.
‡ Below band: the vendor has no config at the role's floor; this is its best one.
Marks follow each config's own evidence, including on the hand overrides.

`max` is ignored: no default cell uses it, and `place` and `rank` leave it out of
the candidates, the frontier and the quality fits. It is the one tier with no
discount and the worst cache price, and it does not reflect real use. Its measured
cost is still used as an anchor to price cheaper efforts of the same model, since
Opus, Sonnet and Haiku 5.5 are only costed at `max`. Use `max` only when the user
asks. `place` never edits this file.

### What each role is

| Role | Job |
|---|---|
| `deterministic` | The CLI is the worker. Model only invokes a local tool. Cheap to verify. Examples: `tesseract-cli`, `diff-image`, `agentctl`. |
| `explore` | Read-only gather: logs, diffs, docs, health. Not Jira evidence capture. Return paths, commands, timestamps, exact failures, and confidence. Cursor `subagent_type: explore`. |
| `follow` | Execute an already-written skill/procedure (commit-message drafting, worklogs). Do not invent scope. No approval decisions. |
| `plan` | Write a spec or plan of one surface from a PRD (`plan-implementation`, `plan-task-evidence`). |
| `build` | Execute a plan or bounded coding of one surface (`run-plan`, `develop-*`). |
| `impl-review` | Review a delivery against its plan (`validate-impl`); runs on a different model than the author. |
| `plan-review` | Review and rewrite a plan before work starts (`validate-plan`); runs on a different model than the author. |
| `task-owner` | Substantial independent task (worktree / key). May coordinate children if authorized (`orchestrate`, `multitask-same-repo`, bootstrap, upgrade). |
| `quality-gate` | Architecture, security, release, or stress-test (`grilling`). Recommendation only: the root and user decide. |

`follow` is not `deterministic`: `tesseract-cli` is a tool run; `follow` still needs a model to walk an already-written procedure.

`inherit` is not a placed role and has no row: the skill runs on the session's own model and effort (`handoff`).

### Notes

- **2026-11-10 rebalance**: the previous bands were fractions of the best measured config
  (Opus 5.5 `xhigh`, 61.8), so every new top model raised every role's floor and pushed
  efforts up, while newer small models do the old work. Floors are now absolute
  Terminal-Bench points (`benchmarks/bands.yaml`), anchored on the operator's report:
  work done on Opus 4.8 `medium` is now done by Haiku 5.5 `high`. Opus 4.8 `max` is
  measured at 23.6, so `medium` sits below that, and Haiku 5.5 `high` converts to 35.9 ± 3.8.
  Mapping that report onto `plan` and `build` is an assumption, not something the operator
  said. `plan` and `build` need 30 (Haiku `high` clears it, `medium` does not), `explore` 22,
  `follow` 25, `deterministic` 12, the reviews 40 (a margin over a Haiku author, so they
  force a stronger and different model), `task-owner` 45, `quality-gate` 52 (the measured
  top cluster: GPT-6 Astra `low` 50.2, Opus 5 `high` 50.4, Fable 5.1 `medium` 53.0).
- **Evidence quality**: Haiku, Sonnet and Opus 5.5 scores rest on Artificial Analysis alone
  (n=9 shared configs, leave-one-out RMSE 3.8), because Terminal-Bench measures them only
  at `max`. No independent coding benchmark exists for Haiku 5.5 yet. Treat every Claude
  cell below `quality-gate` as provisional and use the escalation rule above. Re-check when
  Terminal-Bench or DeepSWE measures Haiku 5.5.
- **Cost fix**: Haiku 5.5 `low`/`medium`/`high` had no cost estimate, and `place` sorts
  missing costs last, which forced Haiku `xhigh` onto three roles. `estimate_costs` now
  scales the list price through the effort ladder, so the cheaper efforts compete.
- **Claude**: Haiku 5.5 now covers `deterministic` through `build`. Sonnet 5.5 is not in
  the table: it matches Haiku `high` at `medium` (36.8 against 35.9) for 20 times the list
  price, and for the reviews and `task-owner` it costs more per task than Opus 5.5
  `medium` ($5.4 `medium`, $8.2 `high` against $3.45), though those Sonnet costs are
  ladder estimates from its `max` run, not measured. Spawn Sonnet only when the user
  names it. Fable 5.1 is never the cheapest config.
  Haiku 4.5 is below the `deterministic` floor.
- **Codex**: `place` picked GPT-6.1 Sol for the reviews too, which would put author and
  reviewer on one model. Hand override: GPT-6 Astra `low` (50.2, measured) for `impl-review`
  and `plan-review`, and Astra `medium` (54.5, measured) for `quality-gate`, where place
  chose Sol `xhigh` on Artificial Analysis alone. Place chose Luna `high`/`xhigh` for
  `explore`/`follow` by clearing the floor by about 1 point; Sol `low` clears it by 12 or more.
  GPT-6 Luna stays the `deterministic` slot.
- **Cursor** (Composer + Grok only): Grok 4.7 effort buys almost nothing in the data
  (`low` 37.1 and `high` 41.2 are Artificial Analysis estimates, `xhigh` 38.3 is measured),
  so the cheap effort wins wherever it clears the floor. Hand override: `plan-review` and
  `quality-gate` keep `xhigh`, the only measured Grok 4.7 config, since `high` does not beat
  it beyond noise. One model family means no different-model reviewer; reviews rely on
  effort and a fresh session. Composer 2.5 (hand guess) and `auto` (no data) fall below the
  `deterministic` floor. Grok 4.7 `medium` has no score and is not used.

## Skills

Canonical skills only. Aliases are not extra directories: they live in
`metadata.aliases` and are pipe-appended onto `description` with
`recommendedRole`. Vendor overrides (`orchestrate`, `graphify`,
`impeccable`) keep the same role across harnesses; the table above supplies
the model/effort.

| Skill | `recommendedRole` | Why |
|---|---|---|
| `blank-space` | `deterministic` | Local image metric CLI |
| `color-palette` | `deterministic` | Local palette extract/score CLI |
| `diff-image` | `deterministic` | Local pixel-diff CLI |
| `dsnote` | `deterministic` | Offline TTS/STT CLI |
| `google-translate` | `deterministic` | Translation API CLI |
| `render-diff-patch` | `deterministic` | Diff → HTML/screenshot CLI |
| `tesseract-cli` | `deterministic` | OCR CLI |
| `wait-what` | `deterministic` | Tiny re-pitch instruction |
| `export-canvas-html` | `deterministic` | Cursor only. `.canvas.tsx` → HTML via official canvas-runtime |
| `check-disk-cleanup` | `deterministic` | Read-only `agentctl disk` clean-up scan |
| `skillspector` | `deterministic` | Static SkillSpector scan CLI |
| `debug-xp-app` | `explore` | Build/runtime diagnosis |
| `describe-image` | `explore` | Local vision description |
| `find-related-issues` | `explore` | Read-only scan of related and parallel issues, plus a status brief of one |
| `read-figma` | `explore` | Local `.fig` decode/inspect |
| `find-skills` | `follow` | Defined `npx skills` install flow |
| `generate-worklogs` | `follow` | Defined daily worklog procedure |
| `playwright-cli` | `follow` | External package skill; not edited |
| `use-enonic-cli` | `follow` | Defined Enonic CLI procedure |
| `apply-react4xp-practices` | `build` | Conventions while writing/reviewing React4XP code |
| `develop-godot` | `build` | Bounded game-dev implementation |
| `develop-react4xp-v5` | `build` | Bounded React4XP 5.x implementation |
| `develop-react4xp-v6` | `build` | Bounded React4XP 6.x implementation |
| `develop-react4xp-v7` | `build` | Bounded React4XP 7.x implementation |
| `develop-xp7-backend` | `build` | Bounded XP 7 backend implementation |
| `develop-xp8` | `build` | Bounded XP 8 implementation / docs |
| `draft-commit-message` | `follow` | Commit message from a real diff |
| `handoff` | `inherit` | Runs on the session model |
| `imagine-design` | `build` | Consistent asset generation under an imagine design.json |
| `humanize-text` | `build` | Prose rewrite with judgment |
| `impeccable` | `build` | UI design/implementation (audit mode can bump to `quality-gate`) |
| `lint-and-draft-commit-message` | `follow` | Lint/fix + commit message (python / PHP / Enonic / generic, lazy-loaded) |
| `download-jira-task` | `follow` | `agentctl jira fetch` CLI |
| `draw-diagram` | `follow` | Defined Excalidraw diagram procedure |
| `harvest-kb` | `follow` | Defined digest to KB proposals procedure |
| `set-up-worktree` | `follow` | Defined worktree setup procedure |
| `spawn-playwright-mcp` | `follow` | Defined Playwright MCP spawn procedure |
| `ponytail-review` | `impl-review` | Over-engineering review of a delivery diff |
| `plan-implementation` | `plan` | One-ticket spec |
| `plan-task-evidence` | `plan` | Authors `*-evidence-plan.md` (Jira evidence plan, not `explore`) |
| `plan-data-rehearsal` | `plan` | Rehearsal plan for shared-data writes |
| `propose-harness-changes` | `plan` | Harness proposals from a scan signals file |
| `write-prd` | `plan` | Local PRD from a raw request |
| `run-plan` | `build` | Execute one plan |
| `test-xp-apps` | `build` | Test structure and verification |
| `validate-evidence` | `impl-review` | Captured evidence review against the evidence plan (report only) |
| `validate-imagine` | `impl-review` | Imagine lake review/fix against the original concept |
| `validate-impl` | `impl-review` | Delivery review/fix |
| `validate-plan` | `plan-review` | Plan review/rewrite |
| `write-analyst-message` | `build` | Client-facing copy with judgment |
| `graphify` | `task-owner` | Independent graph pipeline + synthesis |
| `imagine` | `task-owner` | Creative research + subagent world expansion |
| `multitask-same-repo` | `task-owner` | Multi-worktree coordination |
| `orchestrate` | `task-owner` | Independent task split |
| `set-up-enonic-react4xp` | `task-owner` | New project bootstrap |
| `upgrade-xp-app` | `task-owner` | XP 7 → 8 migration |
| `grilling` | `quality-gate` | Stress-test a plan/decision |
| `audit-heavy-report` | `quality-gate` | Five-category security audit report |
| `classify-ticket-autonomy` | `quality-gate` | Autonomy verdict against fixed criteria |
