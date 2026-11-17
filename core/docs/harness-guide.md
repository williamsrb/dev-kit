# Using the harness

The harness is one shared tree of skills, rules, knowledge base (KB), hooks and the `agentctl` CLI. Claude Code, Codex and Cursor all read from it, so a skill or rule written once applies in all three.

This guide is for the person driving the agent. The KB How-tos under `kb/` are written for agents and are deliberately terse; read them when you want the exact procedure behind a step.

## Where it lives

| Install | Harness root |
|---|---|
| Direct (maintainer machine) | `~/.agents` |
| devkit profile | `~/.agents-profiles/<profile>/agents`, exported as `$AGENTS_HOME` |

Paths below are relative to the harness root. In a profile, `agentctl` and the vendor CLIs on the profile's `PATH` already point at the right root.

| Folder | What it holds |
|---|---|
| `skills/` | Skills: one folder per task type, each with a `SKILL.md` the agent loads on demand |
| `rules/` | Always-on instructions. `BASE.md` is the contract; `manifest.json` lists the sections; bodies come from the `.mdc` rules or `agents.d/`, and `bin/generate-agents-md.py` builds `AGENTS.md` and `rules/claude/` |
| `kb/` | How-tos (`implementation/`, `testing/`, `validation/`), offline vendor docs (`offline-reference/`), shared writing guides (`_shared/`) |
| `hooks/` | Scripts the vendors run on prompts and tool calls: git and Jira guards, history log, KB router, reply format check |
| `bin/` | `agentctl` and the helper scripts skills call |
| `mcp/` | Installers for the MCP servers and the on-demand Playwright MCP |
| `agents/` | Subagent definitions |
| `skills-vendor/` | Per-vendor skill variants, and `ROLES.md`, which maps task roles to models |
| `config/` | Factory pipelines and the client overlay example |
| `.agentctl` | TOML with every `agentctl` default: tracker, git policy, factory, hooks |
| `prds/`, `plans/` | Per-task inputs and plans. Local only, never exported |
| `history/` | Automatic log of every prompt and reply. Local only |

## First day

1. Install through the kit (`devkit` README, steps 1 to 3), then run `devkit doctor`.
2. Check the local CLIs the skills depend on: `agentctl tools audit`. Install what it reports missing.
3. For Jira work, create `.auth/jira-api-token.yaml` under the harness root with `user` (your Atlassian email), `api_token` and optionally `site`, readable only by you (`chmod 600`). Then try `agentctl jira myself`.
4. Start the profile (`claude-<name>`, `codex-<name>`, or Cursor through its wrapper) inside the repo you work on.

## Talking to the agent

The agent follows `rules/BASE.md`. What that means in practice:

- **Answers come first.** Replies open with the result, then evidence, then the next step. Markers have one meaning each (✅ verified, ⛔ failed, 🚫 blocker, ⚠️ risk, ❓ question for you, 👉 next action).
- **It asks before anything hard to undo.** Commit, reset, rebase, schema or auth changes, and widening scope wait for an explicit order. "Commit this", "reset", "go ahead" are orders. "Looks good" is not. Push is different: a hook denies it, so you push.
- **Reply keywords are uppercase in quotes.** When the agent offers options it labels them `O1`, `O2`. Keycaps (1️⃣ 2️⃣) mean pick one; circled letters (Ⓐ Ⓑ) mean you can combine them ("A C" or "ALL").
- **Aliases** at the start of a message:
  - `plan`: plan only, no implementation.
  - `mult`: split the request into independent workstreams (`orchestrate` skill).
  - `any`: list what is still pending in this session.
- **Your exclusions win.** "Only change the order" or "leave the header alone" overrides the Figma, the PRD and any plan step that disagrees.

## The task workflow

The charts in [dev-process/](dev-process/STEPS.md) show the full pipeline and which decisions reach a person. Short version:

**Jira task:**
`download-jira-task` → `plan-implementation` → `validate-plan` → `run-plan` → `validate-impl` → `lint-and-draft-commit-message` → `plan-task-evidence` → `validate-plan` → `run-plan` (evidence) → `validate-evidence`

**Local task (no Jira):** start with `write-prd` (from a raw request) or `handoff` (from the current chat). There is no analyst, so the planner picks the recommended option for each open question instead of asking.

**Several tasks on one repo:** name `multitask-same-repo`. It sets up one worktree per task and runs each phase in a fresh session. Do not loop `run-plan` over keys in one session.

Run each phase in a fresh session where the skill says so. Plans and PRDs live on disk (`plans/<TASK-ID>/`, `prds/<KEY>.md`), so a new session picks them up without the chat history.

Use a different model for review than for writing: `validate-plan` and `validate-impl` are reviews.

## Skills by job

Ask in plain words ("plan ABC-123", "lint and commit"); the `kb-router` hook points the agent at the matching skill. Naming the skill also works. Skills marked *named only* run only when you name them.

### Intake and planning

| Skill | Use it to |
|---|---|
| `download-jira-task` | Save a Jira issue with comments and attachments to `prds/<KEY>.md` |
| `write-prd` | Turn a request, email or Slack thread into a local PRD |
| `handoff` | Compact the chat into a context summary or a PRD for another session |
| `find-related-issues` | Find parent, sibling and linked issues and unreleased branches touching the same files |
| `classify-ticket-autonomy` | Decide whether a ticket can run without a human |
| `plan-implementation` | Write the implementation plan from a PRD |
| `plan-task-evidence` | Write the QA evidence plan |
| `validate-plan` | Review and rewrite a plan before work starts |
| `grilling` | Have the agent stress-test your plan or idea |

### Building

| Skill | Use it to |
|---|---|
| `run-plan` | Execute a plan file (*named only*) |
| `multitask-same-repo`, `set-up-worktree` | Parallel tasks on one repo (*named only*) |
| `graft` | Find code through the prebuilt graph in repos that have a `graft/` folder |
| `develop-godot` | Godot 4 games |

### Review and delivery

| Skill | Use it to |
|---|---|
| `validate-impl` | Review and fix the delivery against the requirements |
| `ponytail-review` | Flag over-engineering only; no fixes |
| `draft-commit-message` | Draft a commit message ("commit") |
| `lint-and-draft-commit-message` | Lint, fix, then draft ("lint and commit") |
| `render-diff-patch` | Render a diff as side-by-side HTML |
| `audit-heavy-report` | Five-category security audit with a PDF report |

### Evidence and images

| Skill | Use it to |
|---|---|
| `validate-evidence` | Check captured evidence against its plan |
| `playwright-cli`, `spawn-playwright-mcp` | Drive a headless browser |
| `tesseract-cli` | OCR a screenshot locally |
| `describe-image` | Describe a screenshot with a local vision model first |
| `diff-image`, `blank-space`, `color-palette` | Pixel diff, empty-area ratio, palette conformance |
| `read-figma` | Decode a local `.fig` file and resolve a node id |

### Writing and communication

| Skill | Use it to |
|---|---|
| `write-analyst-message` | Jira comments, TBD questions and Slack messages in product language |
| `generate-worklogs` | Build worklogs for a date from git, Jira and Slack |
| `humanize-text` | Rewrite prose that reads as machine-written |
| `google-translate` | Translate copy |
| `wait-what` | Ask the agent to re-explain its last message |

### Diagrams and creative

| Skill | Use it to |
|---|---|
| `archify` | Interactive HTML diagrams and one-page explainers |
| `draw-diagram` | Editable Excalidraw drawings |
| `imagine`, `imagine-design`, `validate-imagine` | Concept worlds, consistent asset sets, and their review |

### Maintenance

| Skill | Use it to |
|---|---|
| `find-skills` | Find and install a skill from skills.sh |
| `skillspector` | Scan a skill for prompt injection and exfiltration before installing it |
| `check-disk-cleanup` | Read-only disk clean-up report |

**Enonic profile only:** `develop-xp7-backend`, `develop-xp8`, `develop-react4xp-v5` / `v6` / `v7`, `apply-react4xp-practices`, `use-enonic-cli`, `debug-xp-app`, `test-xp-apps`, `set-up-enonic-react4xp` (*named only*), `upgrade-xp-app` (*named only*). Offline XP and React4XP docs ship under `kb/offline-reference/`.

## agentctl

`agentctl` does the mechanical work so the model does not spend tokens on it. Each command prints bounded JSON and leaves raw output on disk. Skills call it for you; you run it directly when you want the same answer without a model.

| Group | Main commands | What for |
|---|---|---|
| `jira` | `fetch`, `search`, `get`, `comment`, `attach`, `transition`, `wiki-get` | Jira and Confluence over REST with your API token |
| `plan` | `init`, `validate`, `progress`, `resolve` | Create and check plan files |
| `delivery` | `scope` | Changed files of the current delivery |
| `repo` | `detect` | Stack, manifests and native checks of a repo |
| `checks`, `security` | `run`, `scan`, `summarize` | Local validators and CI-parity security scans |
| `image`, `evidence` | `stamp`, `diff`, `whitespace`, `describe`, `inspect` | Screenshot checks before anything goes to Jira |
| `playwright` | `spawn`, `revive`, `list`, `stop` | One headless Playwright MCP per task id |
| `factory` | `start`, `status`, `watch`, `resume`, `stop` | Run the task pipeline unattended (below) |
| `docs`, `kb`, `markdown` | `search`, `export`, section select | Search local docs and move the KB |
| `local` | `run`, `models` | Low-risk summaries on local Ollama |
| `tools` | `audit`, `update` | Check and update the CLIs skills need |
| `worklog`, `release`, `sync`, `subagents`, `disk`, `bench`, `git`, `logs`, `code`, `skills`, `task` | | See `agentctl <group> --help` |

Examples:

```bash
agentctl jira fetch ABC-123
agentctl repo detect --cwd .
agentctl delivery scope --cwd .
agentctl logs extract server.log --limit 20
agentctl evidence inspect shot.png --ocr --expected-text 'Saved'
```

## Hooks: what gets blocked

Hooks run on every session. When one stops the agent, it is policy, not a bug.

| Hook | Effect |
|---|---|
| `claude-git-guard.py` (Claude Code, Codex), `deny-git-push.sh` (Cursor) | Both deny `git push` in any form and ask before `commit`, `reset`, `rebase`, `clean`. Only the first also denies fast-forward merges and commits with `Co-authored-by`. Push yourself; the factory pushes only its task branch, per `.agentctl [git.factory]`. |
| `jira-write-guard.py` | Denies the tracker MCP comment and attachment tools. Comments go through `agentctl jira comment --confirm-issue <KEY>`, which also backs up a comment before editing it. |
| `response-format-check.py` | Blocks a reply whose list or marker lines would render as a code block, so the agent rewrites it. |
| `kb-router.py` | Matches your prompt against skills and KB indexes and shows the agent the hits. |
| `history.py` and adapters | Log every prompt and reply under `history/<date>/`. |
| `graft-hooks.cjs`, `graft-guard.py` | Graft status line and undo of graft's own config rewrites. |

## Rules worth knowing

The full set is `rules/BASE.md` plus the sections in `rules/manifest.json`. The ones that change what you see:

- **Git:** the agent never stages or commits without an order, and only the factory engine pushes. Merges are always `--no-ff`. Its edits stay unstaged, so staged changes are your baseline.
- **Jira evidence:** an evidence comment is posted only when every step passed. On any failure the agent reports in chat and does not post. Every screenshot is checked (`agentctl image stamp --check`) before upload.
- **Client-facing text** (Jira comments, review request descriptions, Slack) is written in product language, addressed to the analyst, with the recommended option first. Chat with you stays terse.
- **Local first:** OCR, log extraction, diff scoping and similar work go through local CLIs, not the model.
- **Browser:** Playwright is the browser. The agent uses a vendor's built-in browser only when you name it.
- **Unattended runs:** in headless or "I'm leaving" runs, the agent skips any step that would prompt and lists the exact commands at the end for you to run.

## The knowledge base

Every task can write a `How-to-*.md` back into `kb/`, so the next task asks fewer questions. When the agent learns something reusable (a project quirk, a fixed failure), expect it to propose a How-to. How to write one: `kb/_shared/How-to-author-ai-howtos.md`.

`kb/offline-reference/` holds vendor docs so the agent reads the right version instead of guessing from training data.

## The factory

`agentctl factory start <TASK>` runs the whole pipeline in fresh headless sessions and stops at `awaiting_human_review`. Run it from the task's repo with the task branch checked out; it never creates or switches branches.

```bash
agentctl factory start ABC-123 --dry-run   # steps, models and gates, no model call
agentctl factory start ABC-123
agentctl factory watch ABC-123 --progress
agentctl factory status
agentctl factory resume ABC-123            # after you clear a parked step
```

A step that needs a person (an analyst question, a gated git write, a failed check) parks the run instead of guessing. Details: `kb/implementation/How-to-run-the-dark-factory.md`.

## When something goes wrong

- **A skill or CLI is missing:** `agentctl tools audit`, then `devkit doctor`.
- **The browser MCP disappeared** (after a reboot): name `spawn-playwright-mcp`, or run `agentctl playwright revive`.
- **A git or Jira call was denied:** a hook did it on purpose. Run the command yourself or give the order the rule asks for.
- **The agent stopped with a question in an unattended run:** that step was gated. The end-of-run list has the command.
- **Kit-level problems** (profiles, wrappers, updates): `docs/troubleshooting.md` in the devkit repo.
