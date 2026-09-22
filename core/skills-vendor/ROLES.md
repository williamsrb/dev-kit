# Roles → vendor model / effort

Human lookup only. Not a routing signal for agents. Defaults follow
`~/.agents/benchmarks/2026-08-deepswe.yaml` (closest score under ~2× cost;
roles collapse when a vendor has no Luna/Terra/Sol ladder).

When you explicitly call a skill, read `metadata.recommendedRole` in that
skill’s `SKILL.md`, then pick the row below for the harness you are in.

**Evidence** in this harness means Jira/QA after delivery. It is not a role.

## Roles

Sorted cheapest/simplest first.

| Role | Codex | Claude | Cursor |
|---|---|---|---|
| `deterministic` | `gpt-5.6-luna` `high` | `claude-4.5-haiku` default | `auto` |
| `explore` | `gpt-5.6-luna` `xhigh` | `claude-opus-5` `low` | `composer-2.5-fast` |
| `follow` | `gpt-5.6-luna` `xhigh` | `claude-opus-5` `low` | `composer-2.5-fast` |
| `implement` | `gpt-5.6-luna` `max` | `claude-opus-5` `medium` | `cursor-grok-4.7-medium` |
| `task-owner` | `gpt-5.6-terra` `xhigh` | `claude-opus-5` `medium` | `cursor-grok-4.7-medium` |
| `quality-gate` | `gpt-5.6-sol` `medium` | `claude-opus-5` `high` | `cursor-grok-4.7-high` |

### What each role is

| Role | Job |
|---|---|
| `deterministic` | The CLI is the worker. Model only invokes a local tool. Cheap to verify. |
| `explore` | Read-only gather: logs, diffs, docs, health. Not Jira evidence capture. |
| `follow` | Execute an already-written skill/procedure. Do not invent scope. |
| `implement` | Bounded coding, spec, review, or plan of one surface. |
| `task-owner` | Substantial independent task (worktree / key). May coordinate children if authorized. |
| `quality-gate` | Architecture, security, release, or stress-test. Recommendation only. |

`follow` is not `deterministic`: `tesseract-cli` is a tool run; `download-jira-task` still needs a model to walk MCP/CLI steps.

### Notes

- **Cursor** has no Luna/Terra/Sol product ladder. Route like Claude’s
  effort split: `composer-2.5-fast` for `explore`/`follow`,
  `cursor-grok-4.7-medium` for `implement`/`task-owner`,
  `cursor-grok-4.7-high` for `quality-gate`, `auto` for `deterministic`.
  Grok 4.7 has no DeepSWE rows yet — provisional until a new benchmark file.
- **Claude** collapses Luna max, Terra xhigh, and Sol medium coding into Opus
  `medium`. `quality-gate` is Opus `high` (DeepSWE High already matches Sol xhigh).
- **Codex** `deterministic` is Luna `high` only (Haiku analogue). Do not use
  Luna medium or low for SWE.
- **`quality-gate` (Codex):** bump to Sol `xhigh` only when consequence is extreme
  (architecture, security, payment, release-risk). Cursor uses
  `cursor-grok-4.7-high` for that slot.

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
| `context7-mcp` | `explore` | Library/docs lookup |
| `debug-xp-app` | `explore` | Build/runtime diagnosis |
| `describe-image` | `explore` | Local vision description |
| `read-figma` | `explore` | Local `.fig` decode/inspect |
| `download-jira-task` | `follow` | Defined Jira → `prds/` fetch |
| `find-skills` | `follow` | Defined `npx skills` install flow |
| `generate-worklogs` | `follow` | Defined daily worklog procedure |
| `playwright-cli` | `follow` | External package skill; not edited |
| `use-enonic-cli` | `follow` | Defined Enonic CLI procedure |
| `apply-react4xp-practices` | `implement` | Conventions while writing/reviewing React4XP code |
| `develop-godot-2d` | `implement` | Bounded game-dev implementation |
| `develop-godot-3d` | `implement` | Bounded game-dev implementation |
| `develop-react4xp-v5` | `implement` | Bounded React4XP 5.x implementation |
| `develop-react4xp-v6` | `implement` | Bounded React4XP 6.x implementation |
| `develop-react4xp-v7` | `implement` | Bounded React4XP 7.x implementation |
| `develop-xp7-backend` | `implement` | Bounded XP 7 backend implementation |
| `develop-xp8` | `implement` | Bounded XP 8 implementation / docs |
| `draft-commit-message` | `implement` | Commit message from a real diff |
| `handoff` | `implement` | Conversation compact with judgment |
| `humanize-text` | `implement` | Prose rewrite with judgment |
| `impeccable` | `implement` | UI design/implementation (audit mode can bump to `quality-gate`) |
| `lint-and-draft-enonic-commit-message` | `implement` | Lint/fix + commit message |
| `lint-and-draft-generic-commit-message` | `implement` | Lint/fix + commit message |
| `plan-implementation` | `implement` | One-ticket spec |
| `plan-task-evidence` | `implement` | Authors `*-evidence-plan.md` (Jira evidence plan, not `explore`) |
| `run-plan` | `implement` | Execute one plan |
| `test-xp-apps` | `implement` | Test structure and verification |
| `validate-impl` | `implement` | Delivery review/fix |
| `validate-plan` | `implement` | Plan review/rewrite |
| `write-analyst-message` | `implement` | Client-facing copy with judgment |
| `graphify` | `task-owner` | Independent graph pipeline + synthesis |
| `multitask-same-repo` | `task-owner` | Multi-worktree coordination |
| `orchestrate` | `task-owner` | Independent task split |
| `set-up-enonic-react4xp` | `task-owner` | New project bootstrap |
| `upgrade-xp-app` | `task-owner` | XP 7 → 8 migration |
| `grill-me` | `quality-gate` | Wrapper; same as `grilling` |
| `grilling` | `quality-gate` | Stress-test a plan/decision |
