When the user wants **multiple PRD tasks on the same repo at once** (same Epic/Release or local slugs; batch implement, parallel worktrees/branches, several PRD→plan→impl flows), read and follow the `multitask-same-repo` skill immediately.

The BASE alias `mult` does **not** activate this rule. `mult` loads the `orchestrate` skill and splits any ordinary prompt. This skill is for same-repo PRD work (Jira keys or local slugs), not ordinary prompt-splitting.

Hard constraints:

1. **Isolation = `git worktree`**, not full repo copies. Never triplicate `node_modules`/build trees. One parent checkout; one worktree (+ branch) per task key.
2. **Subagents do not share a context window.** Share only via disk: PRDs, plans, a short `DECISIONS.md`. Spawn briefs are self-contained and thin — cite those files; forbid re-deriving shared conventions.
3. **Phase-split into fresh sessions.** Do not keep plan-validation and implementation (or QA) in one transcript. `/model` does **not** reset context.
4. **Shared work once, before fan-out.** Helpers, path rules, and cross-cutting ports happen in one pass. Never "identical port into each worktree" inside parallel agents.
5. **One implementer per worktree.** Orchestrator stays thin; each agent is confined to its path and asserts `git branch --show-current` matches the task key before edits.
6. **QA / lint / evidence = fresh session(s)**, preferably one per branch.

Anti-patterns: full `cp -a`/clone-per-task; validate → implement → fix shared mistakes all in one session; each subagent re-reading the same skill and re-porting libs; parent holding every plan's research dump while orchestrating.

Single task/branch → ignore this rule; normal single-flow skills apply.
