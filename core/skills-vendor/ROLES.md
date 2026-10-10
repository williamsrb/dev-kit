# Roles → vendor model / effort

Human lookup only. Not a routing signal for agents. The table is
`agentctl bench place` output (2026-10-09, `~/.agents/benchmarks/placement.yaml`):
every benchmark in `latest.yaml` (Terminal-Bench 4.0, DeepSWE, Artificial
Analysis) converted to Terminal-Bench points, then each vendor gets the cheapest
config whose score minus one standard error clears the role's absolute floor in
`benchmarks/bands.yaml`. Spawnable configs: `benchmarks/harness.yaml`. Refresh with
`agentctl bench collect`, then `agentctl bench place --markdown`.

When you explicitly call a skill, read `metadata.recommendedRole` in that
skill’s `SKILL.md`, then pick the row below for the harness you are in.

**Evidence** in this harness means Jira/QA after delivery. It is not a role.

## Roles

Sorted cheapest/simplest first.

| Role | Codex | Claude | Cursor |
|---|---|---|---|
| `deterministic` | `gpt-6-luna` `max` | `claude-haiku-5-5` `high` † | `cursor-grok-4.7-low` † |
| `explore` | `gpt-6.1-sol` `medium` † | `claude-haiku-5-5` `max` † | `cursor-grok-4.7-xhigh` |
| `follow` | `gpt-6.1-sol` `medium` † | `claude-haiku-5-5` `max` † | `cursor-grok-4.7-xhigh` |
| `implement` | `gpt-6.1-sol` `high` † | `claude-opus-5-5` `medium` † | `cursor-grok-4.7-xhigh` ‡ |
| `task-owner` | `gpt-6.1-sol` `max` | `claude-opus-5-5` `xhigh` † | `cursor-grok-4.7-xhigh` ‡ |
| `quality-gate` | `gpt-6-astra` `max` ‡ | `claude-opus-5-5` `max` | `cursor-grok-4.7-xhigh` ‡ |

† Provisional: one evidence source (mostly Artificial Analysis) or an estimated cost.
‡ Below band: the vendor has no config at the role's floor; this is its best one.

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

- **Bands** (fraction of the frontier, Opus 5.5 `max` at 65.2 Terminal-Bench
  points): `quality-gate` within 2 SE of the frontier (62.1), `task-owner` 0.85
  (55.4), `implement` 0.75 (48.9), `explore`/`follow` 0.45 (29.4),
  `deterministic` 0.20 (13.0). One floor for all vendors.
- **Claude**: Haiku 5.5 replaces Haiku 4.5 (4.5 converts to ~0, below the
  `deterministic` floor). Sonnet 5.5 and Fable 5.1 are never the cheapest config
  in any band.
- **Codex**: GPT-6.1 Sol covers `explore` through `task-owner`; GPT-6 Luna `max`
  is the `deterministic` slot. Nothing Codex offers reaches the `quality-gate`
  floor; GPT-6 Astra `max` (58.0) is the best it has. GPT-5.6 Luna/Terra/Sol are
  never the cheapest config in any band.
- **Cursor** (Composer + Grok only): Grok 4.7 `xhigh` (37.8) is below the
  `implement` floor, so `implement`, `task-owner`, and `quality-gate` are below
  band. Composer 2.5 (hand guess) and `auto` (no data) fall below the
  `deterministic` floor.

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
| `excalidraw-diagrams` | `follow` | Defined `excalidraw-cli` diagram procedure |
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
| `lint-and-draft-commit-message` | `implement` | Lint/fix + commit message (python / PHP / Enonic / generic, lazy-loaded) |
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
